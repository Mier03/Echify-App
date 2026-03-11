import React, { useEffect, useRef, useState } from "react";
import { StyleSheet, Text, View, ActivityIndicator } from "react-native";
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
  const [isCameraReady, setIsCameraReady] = useState(false);
  const [cameraError, setCameraError] = useState("");

  useEffect(() => {
    console.log("Camera permission object:", permission);
  }, [permission]);

  useEffect(() => {
    let isMounted = true;

    const initializeCamera = async () => {
      try {
        if (permission?.granted === true) {
          if (isMounted) setIsInitialized(true);
          return;
        }

        if (permission?.canAskAgain !== false) {
          const result = await requestPermission();
          console.log("requestPermission result:", result);
        }

        if (isMounted) setIsInitialized(true);
      } catch (error) {
        console.error("Camera permission error:", error);
        if (isMounted) {
          setCameraError("Camera permission error");
          setIsInitialized(true);
        }
      }
    };

    const timer = setTimeout(() => {
      initializeCamera();
    }, 300);

    return () => {
      isMounted = false;
      clearTimeout(timer);
    };
  }, [permission, requestPermission]);

  useEffect(() => {
    const inspectDevices = async () => {
      try {
        if (
          permission?.granted &&
          typeof navigator !== "undefined" &&
          navigator.mediaDevices &&
          navigator.mediaDevices.enumerateDevices
        ) {
          const devices = await navigator.mediaDevices.enumerateDevices();
          const videoInputs = devices.filter((d) => d.kind === "videoinput");
          console.log("Video inputs after permission:", videoInputs);

          if (videoInputs.length === 0) {
            setCameraError("No browser camera detected");
          } else {
            setCameraError("");
          }
        }
      } catch (err) {
        console.log("enumerateDevices error:", err);
        setCameraError("Device check failed");
      }
    };

    inspectDevices();
  }, [permission?.granted]);

  useEffect(() => {
    const testCamera = async () => {
      if (!permission?.granted) return;

      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: false,
        });
        console.log("getUserMedia success:", stream);
      } catch (err) {
        console.error("getUserMedia failed:", err);
        setCameraError("getUserMedia failed");
      }
    };

    testCamera();
  }, [permission?.granted]);

  useEffect(() => {
    if (!isInitialized || !permission?.granted || !isCameraReady) {
      return;
    }

    let isActive = true;
    setIsCapturing(true);

    const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

    const captureLoop = async () => {
      await delay(800);

      while (isActive) {
        try {
          if (!cameraRef.current) {
            await delay(300);
            continue;
          }

          const photo = await cameraRef.current.takePictureAsync({
            base64: true,
            quality: 0.5,
            skipProcessing: false,
          });

          if (photo?.base64) {
            sendFrame(photo.base64);
          }
        } catch (err) {
          console.log("Frame capture error:", err);
        }

        await delay(700);
      }
    };

    captureLoop();

    return () => {
      isActive = false;
      setIsCapturing(false);
    };
  }, [isInitialized, permission?.granted, isCameraReady]);

  if (!isInitialized) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#4CAF50" />
        <Text style={styles.loadingText}>Initializing camera...</Text>
      </View>
    );
  }

  if (!permission?.granted) {
    return (
      <View style={styles.loadingContainer}>
        <Text style={styles.loadingText}>Camera permission not granted</Text>
        <Text style={styles.loadingSubtext}>
          Check Chromium site settings and reload the page.
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <ExpoCameraView
        ref={cameraRef}
        style={styles.camera}
        facing="back"
        mute={true}
        onCameraReady={() => {
          console.log("Camera ready");
          setCameraError("");
          setIsCameraReady(true);
        }}
      />

      <View style={styles.statusIndicator}>
        <View style={[styles.statusDot, isCapturing && styles.statusDotActive]} />
        <Text style={styles.statusText}>
          {cameraError
            ? cameraError
            : isCapturing
            ? "Capturing..."
            : isCameraReady
            ? "Ready"
            : "Idle"}
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
    textAlign: "center",
  },
  loadingSubtext: {
    marginTop: 8,
    fontSize: 14,
    color: "#666",
    textAlign: "center",
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