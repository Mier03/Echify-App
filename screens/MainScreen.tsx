import { Audio } from "expo-av";
import React, { useEffect, useRef, useState } from "react";
import {
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
  ScrollView,
} from "react-native";
import { connectSocket, closeSocket } from "../services/socket";
import { sendAudioForSTT } from "../services/stt";

import AudioWave from "../components/AudioWave";
import CameraComponent from "../components/CameraView";

export default function MainScreen() {
  const [activeTab, setActiveTab] = useState<"sign" | "speech">("sign");

  // Sign-to-speech state
  const [typedText, setTypedText] = useState("");
  const [finalWord, setFinalWord] = useState("");
  const newWordStartedRef = useRef(false);

  // Speech-to-text state
  const [isRecording, setIsRecording] = useState(false);
  const [sttText, setSttText] = useState("Say something...");

  const recordingRef = useRef<Audio.Recording | null>(null);
  const silenceTimerRef = useRef(0);
  const speechStartedRef = useRef(false);
  const speechDurationRef = useRef(0);

  const isStoppingRef = useRef(false);
  const isUploadingRef = useRef(false);
  const shouldContinueSpeechRef = useRef(false);

  // --- BACKEND SOCKET LOGIC ---
  useEffect(() => {
    if (activeTab === "sign") {
      connectSocket(async (data) => {
        const committed = data?.committed_letter;
        if (typeof committed === "string" && committed.length > 0) {
          if (!newWordStartedRef.current) {
            setFinalWord("");
            setTypedText("");
            newWordStartedRef.current = true;
          }
          setTypedText((prev) => (prev || "") + committed);
          return;
        }
        const q = data?.queue_text;
        if (typeof q === "string" && q.length > 0) { setTypedText(q); }
        if (data?.should_speak && Array.isArray(data?.letters_to_speak)) {
          const word = data.letters_to_speak.join("");
          if (word.length > 0) { setFinalWord(word); }
          setTypedText("");
          newWordStartedRef.current = false;
        }
      });
    } else {
      closeSocket();
    }
    return () => closeSocket();
  }, [activeTab]);

  // --- SPEECH LOOP LOGIC ---
  useEffect(() => {
    if (activeTab === "speech") {
      shouldContinueSpeechRef.current = true;
      startSpeechLoop();
    } else {
      shouldContinueSpeechRef.current = false;
      stopRecordingAndSend(false, false);
      setIsRecording(false);
    }
    return () => {
      shouldContinueSpeechRef.current = false;
      stopRecordingAndSend(false, false);
    };
  }, [activeTab]);

  const startSpeechLoop = async () => {
    try {
      const { granted } = await Audio.requestPermissionsAsync();
      if (!granted) {
        setSttText("Microphone permission denied.");
        setActiveTab("sign");
        return;
      }
      await Audio.setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true });
      if (shouldContinueSpeechRef.current) { await startRecording(); }
    } catch (e) {
      console.log("startSpeechLoop error:", e);
      setActiveTab("sign");
    }
  };

  const startRecording = async () => {
    try {
      if (!shouldContinueSpeechRef.current || recordingRef.current) return;
      setSttText((prev) => (prev && prev !== "Say something..." && prev !== "Listening...") ? prev : "Listening...");
      setIsRecording(true);
      speechStartedRef.current = false;
      silenceTimerRef.current = 0;
      speechDurationRef.current = 0;
      const rec = new Audio.Recording();
      recordingRef.current = rec;
      await rec.prepareToRecordAsync(Audio.RecordingOptionsPresets.HIGH_QUALITY);
      rec.setProgressUpdateInterval(100);
      rec.setOnRecordingStatusUpdate((status) => {
        if (!status.isRecording) return;
        const db = (status as any).metering;
        if (typeof db !== "number") return;
        if (db > -35) {
          speechStartedRef.current = true;
          silenceTimerRef.current = 0;
          speechDurationRef.current += 0.1;
        } else if (speechStartedRef.current) {
          silenceTimerRef.current += 0.1;
        }
        if (speechStartedRef.current && speechDurationRef.current >= 0.3 && silenceTimerRef.current >= 1.0) {
          if (isStoppingRef.current || isUploadingRef.current) return;
          stopRecordingAndSend(true, true);
        }
      });
      await rec.startAsync();
    } catch (e) {
      setIsRecording(false);
    }
  };

  const stopRecordingAndSend = async (restartAfter: boolean, shouldTranscribe: boolean) => {
    if (isStoppingRef.current) return;
    isStoppingRef.current = true;
    const rec = recordingRef.current;
    if (!rec) { isStoppingRef.current = false; return; }
    try {
      recordingRef.current = null;
      setIsRecording(false);
      await rec.stopAndUnloadAsync();
      const uri = rec.getURI();
      if (!uri || !shouldTranscribe) return;
      if (isUploadingRef.current) return;
      isUploadingRef.current = true;
      setSttText((prev) => prev && prev !== "Say something..." ? prev : "Transcribing...");
      const text = await sendAudioForSTT(uri);
      setSttText((prev) => {
        const t = (text || "").trim();
        if (!t) return prev || "…";
        return t;
      });
    } catch (e) {
      setSttText("STT error.");
    } finally {
      isUploadingRef.current = false;
      isStoppingRef.current = false;
      if (restartAfter && activeTab === "speech" && shouldContinueSpeechRef.current) {
        await startRecording();
      }
    }
  };

  const handleSpeechToggle = async () => {
    if (isRecording) { await stopRecordingAndSend(false, true); } 
    else { shouldContinueSpeechRef.current = true; await startSpeechLoop(); }
  };

  const signBoxText = typedText.length > 0 ? typedText : finalWord.length > 0 ? finalWord : "Waiting for sign...";

  return (
    <View style={styles.container}>
      <View style={styles.mainWrapper}> 
        <View style={styles.tabContainer}>
          <TouchableOpacity
            style={[styles.tab, activeTab === "sign" && styles.activeTab]}
            onPress={() => setActiveTab("sign")}
          >
            <Text style={[styles.tabText, activeTab === "sign" && styles.activeTabText]}>Sign to Speech</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.tab, activeTab === "speech" && styles.activeTab]}
            onPress={() => setActiveTab("speech")}
          >
            <Text style={[styles.tabText, activeTab === "speech" && styles.activeTabText]}>Speech to Text</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.content}>
          {activeTab === "sign" ? (
            <View style={styles.signLayout}>
              <View style={styles.cameraPanel}>
                <CameraComponent />
              </View>
              {/* SCROLLABLE FSL PANEL */}
              <View style={styles.translationPanel}>
                <Text style={styles.translationLabel}>FSL TRANSLATION</Text>
                <ScrollView showsVerticalScrollIndicator={false}>
                    <Text style={styles.translationText}>{signBoxText}</Text>
                </ScrollView>
              </View>
            </View>
          ) : (
            <View style={styles.speechLayout}>
              <View style={styles.speechTopPanel}>
                <View style={styles.waveRow}>
                  <View style={styles.waveWrapper}>
                    <AudioWave isRecording={isRecording} />
                  </View>
                  <TouchableOpacity
                    style={[styles.toggleButton, isRecording ? styles.stopButton : styles.startButton]}
                    onPress={handleSpeechToggle}
                  >
                    <Text style={styles.toggleButtonText}>{isRecording ? "Stop" : "Start"}</Text>
                  </TouchableOpacity>
                </View>
              </View>
              
              {/* SCROLLABLE STT PANEL */}
              <View style={styles.speechBottomPanel}>
                <Text style={styles.translationLabel}>SPEECH TO TEXT</Text>
                <ScrollView showsVerticalScrollIndicator={false}>
                    <Text style={styles.translationText}>{sttText}</Text>
                </ScrollView>
              </View>
            </View>
          )}
        </View>
      </View>
    </View>
  );
}

const THEME = {
  primary: "#8B4E1D",
  background: "#F7F5F3",
  panel: "#FFFFFF",
  text: "#1D2A39",
  muted: "#7C7A76",
  border: "#E0DDD9",
  success: "#4CAF50",
  danger: "#C85A54",
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: THEME.background,
  },
  mainWrapper: {
    flex: 1,
    paddingHorizontal: 20,
    paddingTop: 10,
    paddingBottom: 20,
  },
  tabContainer: {
    flexDirection: "row",
    backgroundColor: "#E2E0DD",
    borderRadius: 34,
    padding: 4,
    marginBottom: 12,
    width: '100%',
    maxWidth: 400,
    alignSelf: 'center',
  },
  tab: {
    flex: 1,
    height: 36,
    borderRadius: 60,
    justifyContent: "center",
    alignItems: "center",
  },
  activeTab: { backgroundColor: THEME.primary },
  tabText: { fontSize: 11, fontWeight: "700", color: THEME.muted },
  activeTabText: { color: "#FFFFFF" },
  content: { flex: 1 },

  // --- SIGN TO SPEECH ---
  signLayout: {
    flex: 1, 
    flexDirection: "row",
    gap: 12,
  },
  cameraPanel: {
    flex: 1.6,
    backgroundColor: "#000",
    borderRadius: 18,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: THEME.border,
  },
  translationPanel: {
    flex: 1,
    backgroundColor: THEME.border,
    borderRadius: 18,
    padding: 18,
    borderWidth: 1,
    borderColor: THEME.border,
    maxHeight: '100%', // Keeps panel from growing
  },

  // --- SPEECH TO TEXT ---
  speechLayout: {
    flex: 1,
    gap: 12,
  },
  speechTopPanel: {
    height: 60, // Slimmer header to fix "too big" issue
    paddingHorizontal: 15,
    justifyContent: "center",
  },
  waveRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  waveWrapper: {
    flex: 1,
    height: 30, // Fixed small height for wave centering
    justifyContent: 'center',
    alignItems: 'center',
    overflow: 'hidden',
  },
  toggleButton: {
    minWidth: 70,
    height: 30,
    borderRadius: 15,
    justifyContent: "center",
    alignItems: "center",
  },
  startButton: { backgroundColor: THEME.success },
  stopButton: { backgroundColor: THEME.danger },
  toggleButtonText: {
    color: "#FFFFFF",
    fontSize: 13,
    fontWeight: "800",
  },
  speechBottomPanel: {
    flex: 1, // Fills remaining space
    backgroundColor: THEME.border,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: THEME.border,
    padding: 24,
  },
  translationLabel: {
    fontSize: 10,
    fontWeight: "800",
    color: THEME.primary,
    marginBottom: 6,
    letterSpacing: 1,
    textTransform: "uppercase",
  },
  translationText: {
    fontSize: 16, // Readable size for the Pi display
    fontWeight: "700",
    color: THEME.text,
    lineHeight: 30,
  },
});