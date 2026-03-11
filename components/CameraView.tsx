import React, { useMemo, useState } from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";

interface CameraViewProps {
  onPrediction?: (prediction: string) => void;
}

export default function CameraView({ onPrediction }: CameraViewProps) {
  const [previewLoaded, setPreviewLoaded] = useState(false);
  const [cameraError, setCameraError] = useState("");

  const previewUrl = useMemo(() => {
    const host =
      typeof window !== "undefined" ? window.location.hostname : "localhost";
    return `http://${host}:8000/preview`;
  }, []);

  return (
    <View style={styles.container}>
      {!previewLoaded && !cameraError && (
        <View style={styles.loadingOverlay}>
          <ActivityIndicator size="large" color="#4CAF50" />
          <Text style={styles.loadingText}>Loading preview...</Text>
        </View>
      )}

      {cameraError ? (
        <View style={styles.loadingContainer}>
          <Text style={styles.loadingText}>Preview unavailable</Text>
          <Text style={styles.loadingSubtext}>
            Check backend stream on port 8000.
          </Text>
        </View>
      ) : (
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
      )}

      <View style={styles.statusIndicator}>
        <View
          style={[styles.statusDot, previewLoaded && styles.statusDotActive]}
        />
        <Text style={styles.statusText}>
          {cameraError ? "Offline" : previewLoaded ? "Live" : "Loading"}
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
    transform: [{ rotate: '180deg' }], 
    WebkitTransform: 'rotate(180deg)',
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