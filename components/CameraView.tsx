import React, { useEffect, useRef, useState } from "react";
import {
  StyleSheet,
  Text,
  View,
  ActivityIndicator,
  TouchableOpacity,
  Linking,
  Platform,
} from "react-native";
import {
  CameraView as ExpoCameraView,
  useCameraPermissions,
} from "expo-camera";
import { sendFrame } from "../services/socket";

interface CameraViewProps {
  onPrediction?: (prediction: string) => void;
}

export default function CameraView({ onPrediction }: CameraViewProps) {
  const [permission, requestPermission] = useCameraPermissions();
  const cameraRef = useRef<any>(null);

  const [isCapturing, setIsCapturing] = useState(false);
  const [isInitialized, setIsInitialized] = useState(false);

  // -----------------------
  // Camera permission
  // -----------------------
  useEffect(() => {
    let isMounted = true;

    const initializeCamera = async () => {
      if (isInitialized) return;

      try {
        if (permission?.granted === true) {
          if (isMounted) setIsInitialized(true);
          return;
        }

        // If browser/app already denied and cannot ask again
        if (permission?.granted === false && permission?.canAskAgain === false) {
          if (isMounted) setIsInitialized(true);
          return;
        }

        const result = await requestPermission();
        console.log("📷 Permission result:", result);

        if (isMounted) setIsInitialized(true);
      } catch (error) {
        console.error("❌ Error requesting camera permission:", error);
        if (isMounted) setIsInitialized(true);
      }
    };

    const timer = setTimeout(() => {
      initializeCamera();
    }, 300);

    return () => {
      isMounted = false;
      clearTimeout(timer);
    };
  }, [permission, requestPermission, isInitialized]);

  // -----------------------
  // Capture loop
  // -----------------------
  useEffect(() => {
    if (!isInitialized || !permission?.granted) {
      console.log("⏸️ Skipping capture:", {
        isInitialized,
        hasPermission: permission?.granted,
      });
      return;
    }

    let isActive = true;
    setIsCapturing(true);
    console.log("▶️ Starting capture loop");

    const captureLoop = async () => {
      // let preview settle first
      await new Promise((r) => setTimeout(r, 1000));

      while (isActive) {
        try {
          if (!cameraRef.current) {
            await new Promise((r) => setTimeout(r, 300));
            continue;
          }

          const photo = await cameraRef.current.takePictureAsync({
            base64: true,
            quality: 0.7,
            skipProcessing: true,
          });

          if (photo?.base64) {
            sendFrame(photo.base64);
          }
        } catch (err) {
          console.log("📸 Frame capture error:", err);
        }

        // ~2 FPS
        await new Promise((r) => setTimeout(r, 500));
      }
    };

    captureLoop();

    return () => {
      console.log("⏹️ Stopping capture loop");
      isActive = false;
      setIsCapturing(false);
    };
  }, [isInitialized, permission?.granted]);

  // -----------------------
  // Actions
  // -----------------------
  const openSettings = () => {
    Linking.openSettings();
  };

  const retryPermission = async () => {
    try {
      const result = await requestPermission();
      console.log("🔄 Retry permission result:", result);
    } catch (error) {
      console.error("❌ Retry permission error:", error);
    }
  };

  // -----------------------
  // RENDER
  // -----------------------
  if (!isInitialized) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#4CAF50" />
        <Text style={styles.loadingText}>Initializing camera...</Text>
        <Text style={styles.loadingSubtext}>
          {permission?.granted ? "Loading..." : "Checking permissions..."}
        </Text>
      </View>
    );
  }

  if (!permission?.granted) {
    return (
      <View style={styles.loadingContainer}>
        <Text style={styles.errorIcon}>📷</Text>
        <Text style={styles.errorTitle}>Camera Access Required</Text>
        <Text style={styles.errorText}>
          This app needs camera permission to recognize sign language gestures.
        </Text>

        <Text style={styles.errorSubtext}>
          {Platform.OS === "web"
            ? "Please allow camera access in your browser."
            : "Please grant camera permission in your device settings."}
        </Text>

        {permission?.canAskAgain === false && Platform.OS !== "web" ? (
          <TouchableOpacity style={styles.settingsButton} onPress={openSettings}>
            <Text style={styles.settingsButtonText}>Open Settings</Text>
          </TouchableOpacity>
        ) : null}

        <TouchableOpacity
          style={
            permission?.canAskAgain === false && Platform.OS !== "web"
              ? styles.retryButton
              : styles.settingsButton
          }
          onPress={retryPermission}
        >
          <Text
            style={
              permission?.canAskAgain === false && Platform.OS !== "web"
                ? styles.retryButtonText
                : styles.settingsButtonText
            }
          >
            Try Again
          </Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <ExpoCameraView
        ref={cameraRef}
        style={styles.camera}
        facing="front"
        mute={true}
      />

      <View style={styles.statusIndicator}>
        <View style={[styles.statusDot, isCapturing && styles.statusDotActive]} />
        <Text style={styles.statusText}>
          {isCapturing ? "Capturing..." : "Idle"}
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#000",
  },
  camera: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "#f5f5f5",
    padding: 20,
  },
  loadingText: {
    marginTop: 16,
    fontSize: 18,
    color: "#333",
    fontWeight: "600",
  },
  loadingSubtext: {
    marginTop: 8,
    fontSize: 14,
    color: "#666",
  },
  errorIcon: {
    fontSize: 64,
    marginBottom: 16,
  },
  errorTitle: {
    fontSize: 22,
    fontWeight: "bold",
    color: "#333",
    marginBottom: 12,
    textAlign: "center",
  },
  errorText: {
    fontSize: 15,
    color: "#666",
    textAlign: "center",
    marginTop: 8,
    paddingHorizontal: 20,
    lineHeight: 22,
  },
  errorSubtext: {
    fontSize: 13,
    color: "#999",
    textAlign: "center",
    marginTop: 8,
    paddingHorizontal: 20,
    lineHeight: 20,
    fontStyle: "italic",
  },
  settingsButton: {
    marginTop: 24,
    backgroundColor: "#4CAF50",
    paddingHorizontal: 32,
    paddingVertical: 14,
    borderRadius: 8,
  },
  settingsButtonText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "700",
  },
  retryButton: {
    marginTop: 12,
    paddingHorizontal: 32,
    paddingVertical: 14,
  },
  retryButtonText: {
    color: "#4CAF50",
    fontSize: 16,
    fontWeight: "600",
  },
  statusIndicator: {
    position: "absolute",
    top: 10,
    right: 10,
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(0,0,0,0.6)",
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: "#ff4444",
    marginRight: 6,
  },
  statusDotActive: {
    backgroundColor: "#44ff44",
  },
  statusText: {
    color: "#fff",
    fontSize: 12,
    fontWeight: "600",
  },
});