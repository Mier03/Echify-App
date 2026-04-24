"""
fsl_dynamic_inference.py
Inference module for FSL dynamic sign language recognition.

Raspberry Pi version using laptop branch model architecture:
- Correct trained model architecture
- Segment-based inference
- Resample collected frames to SEQUENCE_LENGTH
- Adds velocity features before inference
- Raspberry Pi optimization: frame skipping for MediaPipe
"""

import json
import cv2
import mediapipe as mp
import numpy as np
import torch
import torch.nn as nn
from pathlib import Path
import time


# --- Configuration ---
PROJECT_ROOT = Path(__file__).parent.parent.parent
MODEL_PATH = PROJECT_ROOT / 'models' / 'lstm_dynamic_final' / 'final_model_complete.pth'
LABEL_MAP_PATH = PROJECT_ROOT / 'models' / 'lstm_dynamic_final' / 'label_mapping.json'

DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

INPUT_SIZE = 252
SEQUENCE_LENGTH = 30


# --- Gesture segmentation thresholds ---
START_HAND_FRAMES = 2      # need this many consecutive frames with hands to "start" gesture
END_NOHAND_FRAMES = 3       # need this many consecutive frames without hands to "end" gesture
MIN_GESTURE_FRAMES = 3     # ignore gestures shorter than this
COOLDOWN_SECONDS = 0.3      # after a prediction, ignore triggers briefly


# --- Raspberry Pi performance tuning ---
_FRAME_SKIP = 2
_frame_counter = 0
_last_frame_feats = None
_last_hands_detected = False


# --- Model Architecture ---
class ImprovedLSTMModel(nn.Module):
    """
    Laptop branch model architecture.
    Must match the trained checkpoint.
    """
    def __init__(
        self,
        input_size=INPUT_SIZE,
        hidden_size=128,
        num_layers=2,
        num_classes=44,
        dropout=0.5,
    ):
        super().__init__()

        self.input_dropout = nn.Dropout(p=0.1)

        self.conv1 = nn.Conv1d(input_size, 128, kernel_size=3, padding=1)
        self.bn_conv = nn.BatchNorm1d(128)

        self.lstm = nn.LSTM(
            128,
            hidden_size,
            num_layers,
            batch_first=True,
            dropout=dropout,
            bidirectional=True,
        )

        self.fc = nn.Sequential(
            nn.Linear(hidden_size * 2, 128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, num_classes),
        )

    def forward(self, x):
        x = self.input_dropout(x)

        x = x.transpose(1, 2)
        x = torch.relu(self.bn_conv(self.conv1(x)))
        x = x.transpose(1, 2)

        lstm_out, _ = self.lstm(x)
        pooled = torch.mean(lstm_out, dim=1)

        return self.fc(pooled)


# --- Global State ---
model = None
classes = None
label_mapping = None
mp_hands = None
hands = None

collecting = False
gesture_frames = []
consec_hand = 0
consec_nohand = 0
last_prediction_time = 0.0


def normalize_landmarks(landmarks_array: np.ndarray) -> np.ndarray:
    """Normalize landmarks relative to wrist landmark."""
    coords = landmarks_array.reshape(21, 3)
    wrist = coords[0]
    centered = coords - wrist

    max_val = np.max(np.abs(centered))
    if max_val > 0:
        centered = centered / max_val

    return centered.flatten().astype(np.float32)


def load_label_mapping():
    """Load label mapping from JSON file."""
    global label_mapping

    if LABEL_MAP_PATH.exists():
        with open(LABEL_MAP_PATH, 'r', encoding='utf-8') as f:
            label_mapping = json.load(f)
        print(f"✅ Loaded label mapping: {len(label_mapping)} labels")
    else:
        print(f"⚠️ Label mapping not found at {LABEL_MAP_PATH}")
        label_mapping = {}


def get_label(folder_name: str) -> str:
    """Convert folder/class id to readable label."""
    global label_mapping

    if label_mapping and folder_name in label_mapping:
        return label_mapping[folder_name]

    return f"SIGN_{folder_name}"


def initialize_dynamic_model():
    """Load trained model and initialize MediaPipe."""
    global model, classes, mp_hands, hands
    global collecting, gesture_frames, consec_hand, consec_nohand, last_prediction_time
    global _frame_counter, _last_frame_feats, _last_hands_detected

    if model is not None and hands is not None:
        return

    print("=" * 60)
    print("🚀 Initializing FSL Dynamic Recognition System")
    print("=" * 60)

    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"❌ Model not found: {MODEL_PATH}")

    load_label_mapping()

    print(f"📂 Loading model from: {MODEL_PATH}")
    checkpoint = torch.load(MODEL_PATH, map_location=DEVICE)

    classes = checkpoint['classes']
    num_classes = checkpoint['num_classes']
    input_size = checkpoint.get('input_size', INPUT_SIZE)

    best_config = checkpoint.get('best_config', {})
    dropout = best_config.get('Dropout', 0.5)

    print("📊 Model Info:")
    print(f"   - Classes: {num_classes}")
    print(f"   - Device: {DEVICE}")
    if 'test_metrics' in checkpoint and 'f1' in checkpoint['test_metrics']:
        print(f"   - Test F1: {checkpoint['test_metrics']['f1']:.4f}")
    print(f"   - Architecture: hidden=128, layers=2, dropout={dropout}")

    model = ImprovedLSTMModel(
        input_size=input_size,
        num_classes=num_classes,
        dropout=dropout,
    )

    model.load_state_dict(checkpoint['model_state_dict'])
    model.to(DEVICE)
    model.eval()

    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=2,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.6,
    )

    collecting = False
    gesture_frames = []
    consec_hand = 0
    consec_nohand = 0
    last_prediction_time = 0.0

    _frame_counter = 0
    _last_frame_feats = None
    _last_hands_detected = False

    print("✅ Initialization complete!")
    print("=" * 60 + "\n")


def extract_frame_features(frame: np.ndarray) -> tuple[np.ndarray, bool]:
    """
    Extract 126-dim hand landmark features.
    Raspberry Pi optimization: runs MediaPipe every _FRAME_SKIP frames.
    """
    global hands
    global _frame_counter, _last_frame_feats, _last_hands_detected

    _frame_counter += 1

    if (_frame_counter % _FRAME_SKIP) != 0 and _last_frame_feats is not None:
        return _last_frame_feats.copy(), _last_hands_detected

    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(img_rgb)

    frame_feats = np.zeros(126, dtype=np.float32)
    hands_detected = False

    if results.multi_hand_landmarks and results.multi_handedness:
        hands_detected = True

        for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
            label = results.multi_handedness[idx].classification[0].label

            raw_lms = np.array(
                [[lm.x, lm.y, lm.z] for lm in hand_landmarks.landmark],
                dtype=np.float32,
            )

            norm_lms = normalize_landmarks(raw_lms)

            if label == 'Left':
                frame_feats[0:63] = norm_lms
            else:
                frame_feats[63:126] = norm_lms

            mp_drawing = mp.solutions.drawing_utils
            mp_drawing.draw_landmarks(
                frame,
                hand_landmarks,
                mp.solutions.hands.HAND_CONNECTIONS,
            )

    _last_frame_feats = frame_feats.copy()
    _last_hands_detected = hands_detected

    return frame_feats, hands_detected


def resample_sequence(seq: np.ndarray, target_len: int) -> np.ndarray:
    """Resample variable-length sequence to fixed target length."""
    T = seq.shape[0]

    if T == 0:
        return np.zeros((target_len, 126), dtype=np.float32)

    if T == target_len:
        return seq.astype(np.float32)

    idxs = np.linspace(0, T - 1, target_len).astype(int)
    return seq[idxs].astype(np.float32)


def predict_from_sequence(sequence_30: np.ndarray) -> dict:
    """
    Run inference on a sequence.
    Input: (30, 126)
    Adds velocity to become (30, 252).
    """
    global model, classes

    if sequence_30.shape[1] == 126:
        velocity = np.zeros_like(sequence_30)
        velocity[1:] = sequence_30[1:] - sequence_30[:-1]
        sequence_30 = np.concatenate([sequence_30, velocity], axis=1)

    sequence_tensor = torch.from_numpy(sequence_30).unsqueeze(0).float().to(DEVICE)

    with torch.no_grad():
        output = model(sequence_tensor)
        probs = torch.softmax(output, dim=1)

        top3_probs, top3_idx = torch.topk(
            probs,
            k=min(3, len(classes)),
            dim=1,
        )

        top3_probs = top3_probs.cpu().numpy()[0]
        top3_idx = top3_idx.cpu().numpy()[0]

    return {
        'top1_label': get_label(classes[top3_idx[0]]),
        'top1_conf': float(top3_probs[0]),
        'top3_labels': [get_label(classes[i]) for i in top3_idx],
        'top3_confs': [float(p) for p in top3_probs],
        'is_ready': True,
    }


def update_and_maybe_predict(frame: np.ndarray) -> dict:
    """
    Call this every camera frame.
    Collects gesture frames and predicts when gesture ends.
    """
    global collecting, gesture_frames, consec_hand, consec_nohand, last_prediction_time

    feats, hands_detected = extract_frame_features(frame)

    now = time.time()
    in_cooldown = (now - last_prediction_time) < COOLDOWN_SECONDS

    if hands_detected:
        consec_hand += 1
        consec_nohand = 0
    else:
        consec_nohand += 1
        consec_hand = 0

    if not collecting and not in_cooldown and consec_hand >= START_HAND_FRAMES:
        collecting = True
        gesture_frames = [feats]

    elif collecting:
        if hands_detected:
            gesture_frames.append(feats)

        if consec_nohand >= END_NOHAND_FRAMES:
            collecting = False

            if len(gesture_frames) >= MIN_GESTURE_FRAMES:
                seq = np.stack(gesture_frames, axis=0)
                seq30 = resample_sequence(seq, SEQUENCE_LENGTH)
                result = predict_from_sequence(seq30)

                last_prediction_time = now
                gesture_frames = []

                return result

            gesture_frames = []
            return {
                'top1_label': 'Too short / ignored',
                'top1_conf': 0.0,
                'top3_labels': [],
                'top3_confs': [],
                'is_ready': False,
            }

    return {
        'top1_label': "Collecting..." if collecting else "Waiting...",
        'top1_conf': 0.0,
        'top3_labels': [],
        'top3_confs': [],
        'is_ready': False,
        'debug': {
            'collecting': collecting,
            'frames_collected': int(len(gesture_frames)),
            'consec_hand': int(consec_hand),
            'consec_nohand': int(consec_nohand),
            'hands_detected': bool(hands_detected),
        },
    }


def reset_buffer():
    """Manual reset of gesture collection state."""
    global collecting, gesture_frames, consec_hand, consec_nohand
    global _frame_counter, _last_frame_feats, _last_hands_detected

    collecting = False
    gesture_frames = []
    consec_hand = 0
    consec_nohand = 0

    _frame_counter = 0
    _last_frame_feats = None
    _last_hands_detected = False

    print("🔄 Gesture state reset")


def get_model_info():
    """Return model status and config."""
    global classes

    if model is None:
        return {'status': 'not_initialized'}

    return {
        'status': 'ready',
        'num_classes': len(classes),
        'device': str(DEVICE),
        'sequence_length': SEQUENCE_LENGTH,
        'frame_skip': _FRAME_SKIP,
        'segmentation': {
            'START_HAND_FRAMES': START_HAND_FRAMES,
            'END_NOHAND_FRAMES': END_NOHAND_FRAMES,
            'MIN_GESTURE_FRAMES': MIN_GESTURE_FRAMES,
            'COOLDOWN_SECONDS': COOLDOWN_SECONDS,
        },
    }