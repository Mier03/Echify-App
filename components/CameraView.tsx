import React, { useEffect, useMemo, useRef, useState } from "react";
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
  const [previewLoaded, setPreviewLoaded] = useState(false);
  const [cameraError, setCameraError] = useState("");

  const previewUrl = useMemo(() => {
    const host =
      typeof window !== "undefined" ? window.location.hostname : "localhost";
    return `http://${host}:8000/preview`;
  }, []);

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
    if (!isInitialized || !permission?.granted || !isCameraReady) {
      return;
    }

    let isActive = true;
    setIsCapturing(true);

    const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

    const captureLoop = async () => {
      await delay(1000);

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
          Chromium still needs camera permission for hidden frame capture.
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {!previewLoaded && (
        <View style={styles.loadingOverlay}>
          <ActivityIndicator size="large" color="#4CAF50" />
          <Text style={styles.loadingText}>Loading preview...</Text>
        </View>
      )}

      <img
        src={previewUrl}
        alt="Camera Preview"
        style={styles.previewImage as any}
        onLoad={() => {
          setPreviewLoaded(true);
          setCameraError("");
        }}
        onError={() => {
          setPreviewLoaded(false);
          setCameraError("Preview unavailable");
        }}
      />

      <View style={styles.hiddenCameraWrapper}>
        <ExpoCameraView
          ref={cameraRef}
          style={styles.hiddenCamera}
          facing="back"
          mute={true}
          onCameraReady={() => {
            console.log("Hidden camera ready");
            setIsCameraReady(true);
          }}
        />
      </View>

      <View style={styles.statusIndicator}>
        <View
          style={[
            styles.statusDot,
            isCapturing && previewLoaded && styles.statusDotActive,
          ]}
        />
        <Text style={styles.statusText}>
          {cameraError
            ? cameraError
            : isCapturing
            ? "Live + Capturing"
            : previewLoaded
            ? "Preview Ready"
            : "Idle"}
        </Text>
      </View>
    </View>
  );
}

const styles: any = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#000",
    position: "relative",
  },
  previewImage: {
    width: "100%",
    height: "100%",
    objectFit: "cover",
    display: "block",
  },
  hiddenCameraWrapper: {
    position: "absolute",
    width: 1,
    height: 1,
    left: -9999,
    top: -9999,
    overflow: "hidden",
    opacity: 0,
  },
  hiddenCamera: {
    width: 1,
    height: 1,
  },
  loadingOverlay: {
    position: "absolute",
    inset: 0,
    zIndex: 2,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "#111",
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
    zIndex: 3,
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