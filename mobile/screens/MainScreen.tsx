import React, { useEffect, useRef, useState } from "react";
import {
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
  ScrollView,
} from "react-native";
import { connectSocket, closeSocket } from "../services/socket";
import { connectSttSocket, closeSttSocket } from "../services/stt";

import AudioWave from "../components/AudioWave";
import CameraComponent from "../components/CameraView";

export default function MainScreen() {
  const [activeTab, setActiveTab] = useState<"sign" | "speech">("sign");

  const [typedText, setTypedText] = useState("");
  const [finalWord, setFinalWord] = useState("");
  const newWordStartedRef = useRef(false);

  const [isRecording, setIsRecording] = useState(false);
  const [sttText, setSttText] = useState("Say something...");
  const [isSpeechListening, setIsSpeechListening] = useState(false);

  useEffect(() => {
    if (activeTab === "sign") {
      connectSocket((data) => {
        console.log("📩 WS message:", data);

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
        if (typeof q === "string" && q.length > 0) {
          setTypedText(q);
          return;
        }

        const prediction = data?.prediction;
        if (
          typeof prediction === "string" &&
          prediction.length > 0 &&
          prediction !== "UNKNOWN"
        ) {
          setTypedText(prediction);
        }

        if (data?.should_speak && Array.isArray(data?.letters_to_speak)) {
          const word = data.letters_to_speak.join("");

          if (word.length > 0) {
            setFinalWord(word);
          }

          setTypedText("");
          newWordStartedRef.current = false;
        }
      });

      closeSttSocket();
      setIsRecording(false);
      setIsSpeechListening(false);
    } else {
      closeSocket();

      if (isSpeechListening) {
        connectSttSocket((data) => {
          console.log("🎤 STT message:", data);

          if (data?.type === "level") {
            setIsRecording(!!data.isRecording);
          }

          if (data?.type === "transcript") {
            const text = (data.text || "").trim();
            setSttText(text || "…");
          }

          if (data?.type === "error") {
            setSttText(data.message || "STT error.");
            setIsRecording(false);
          }
        });
      } else {
        closeSttSocket();
        setIsRecording(false);
      }
    }

    return () => {
      closeSocket();
      closeSttSocket();
    };
  }, [activeTab, isSpeechListening]);

  const handleSpeechToggle = async () => {
    if (isSpeechListening) {
      setIsSpeechListening(false);
      setIsRecording(false);
      setSttText((prev) =>
        prev && prev !== "Say something..." ? prev : "Say something..."
      );
      closeSttSocket();
    } else {
      setSttText("Listening...");
      setIsSpeechListening(true);
    }
  };

  const signBoxText =
    typedText.length > 0
      ? typedText
      : finalWord.length > 0
      ? finalWord
      : "Waiting for sign...";

  return (
    <View style={styles.container}>
      <View style={styles.mainWrapper}>
        <View style={styles.header}>
          <Text style={styles.brandText}>E C H I F Y</Text>
        </View>

        <View style={styles.tabContainer}>
          <TouchableOpacity
            style={[styles.tab, activeTab === "sign" && styles.activeTab]}
            onPress={() => setActiveTab("sign")}
          >
            <Text
              style={[
                styles.tabText,
                activeTab === "sign" && styles.activeTabText,
              ]}
            >
              Sign to Speech
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.tab, activeTab === "speech" && styles.activeTab]}
            onPress={() => setActiveTab("speech")}
          >
            <Text
              style={[
                styles.tabText,
                activeTab === "speech" && styles.activeTabText,
              ]}
            >
              Speech to Text
            </Text>
          </TouchableOpacity>
        </View>

        <View style={styles.content}>
          {activeTab === "sign" ? (
            <View style={styles.signLayout}>
              <View style={styles.cameraPanel}>
                <CameraComponent />
              </View>

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
                    style={[
                      styles.toggleButton,
                      isSpeechListening ? styles.stopButton : styles.startButton,
                    ]}
                    onPress={handleSpeechToggle}
                  >
                    <Text style={styles.toggleButtonText}>
                      {isSpeechListening ? "Stop" : "Start"}
                    </Text>
                  </TouchableOpacity>
                </View>
              </View>

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

  header: {
    position: "absolute",
    left: 0,
    top: 18,
    zIndex: 10,
    paddingHorizontal: 20,
  },

  brandText: {
    fontSize: 18,
    fontWeight: "800",
    color: THEME.primary,
    letterSpacing: 1,
    textTransform: "uppercase",
  },

  tabContainer: {
    flexDirection: "row",
    backgroundColor: "#E2E0DD",
    borderRadius: 34,
    padding: 4,
    marginBottom: 12,
    width: "60%",
    maxWidth: 300,
    alignSelf: "flex-end",
  },

  tab: {
    flex: 1,
    height: 30,
    borderRadius: 60,
    justifyContent: "center",
    alignItems: "center",
  },

  activeTab: {
    backgroundColor: THEME.primary,
  },

  tabText: {
    fontSize: 11,
    fontWeight: "700",
    color: THEME.muted,
  },

  activeTabText: {
    color: "#FFFFFF",
  },

  content: {
    flex: 1,
  },

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
    flex: 0.7,
    backgroundColor: THEME.border,
    borderRadius: 18,
    padding: 18,
    borderWidth: 1,
    borderColor: THEME.border,
    maxHeight: "100%",
  },

  speechLayout: {
    flex: 1,
    gap: 12,
  },

  speechTopPanel: {
    height: 60,
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
    height: 30,
    justifyContent: "center",
    alignItems: "center",
    overflow: "hidden",
  },

  toggleButton: {
    minWidth: 70,
    height: 30,
    borderRadius: 15,
    justifyContent: "center",
    alignItems: "center",
  },

  startButton: {
    backgroundColor: THEME.success,
  },

  stopButton: {
    backgroundColor: THEME.danger,
  },

  toggleButtonText: {
    color: "#FFFFFF",
    fontSize: 13,
    fontWeight: "800",
  },

  speechBottomPanel: {
    flex: 1,
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
    fontSize: 16,
    fontWeight: "700",
    color: THEME.text,
    lineHeight: 30,
  },
});