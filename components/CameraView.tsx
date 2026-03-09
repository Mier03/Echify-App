// import React, { useEffect, useRef, useState } from "react";
// import { StyleSheet, Text, View, ActivityIndicator } from "react-native";
// import {
//   CameraView as ExpoCameraView,
//   useCameraPermissions,
// } from "expo-camera";
// import { sendFrame } from "../services/socket";

// interface CameraViewProps {
//   onPrediction?: (prediction: string) => void;
// }

// export default function CameraView({ onPrediction }: CameraViewProps) {
//   const [permission, requestPermission] = useCameraPermissions();
//   const cameraRef = useRef<any>(null);

//   const [isCapturing, setIsCapturing] = useState(false);
//   const [isInitialized, setIsInitialized] = useState(false);

//   useEffect(() => {
//     let isMounted = true;

//     const initializeCamera = async () => {
//       try {
//         if (permission?.granted === true) {
//           if (isMounted) setIsInitialized(true);
//           return;
//         }

//         if (permission?.canAskAgain !== false) {
//           await requestPermission();
//         }

//         if (isMounted) setIsInitialized(true);
//       } catch (error) {
//         console.error("Camera permission error:", error);
//         if (isMounted) setIsInitialized(true);
//       }
//     };

//     const timer = setTimeout(() => {
//       initializeCamera();
//     }, 300);

//     return () => {
//       isMounted = false;
//       clearTimeout(timer);
//     };
//   }, [permission, requestPermission]);

//   useEffect(() => {
//     if (!isInitialized || !permission?.granted) {
//       return;
//     }

//     let isActive = true;
//     setIsCapturing(true);

//     const captureLoop = async () => {
//       await new Promise((r) => setTimeout(r, 1000));

//       while (isActive) {
//         try {
//           if (!cameraRef.current) {
//             await new Promise((r) => setTimeout(r, 300));
//             continue;
//           }

//           const photo = await cameraRef.current.takePictureAsync({
//             base64: true,
//             quality: 0.7,
//             skipProcessing: true,
//           });

//           if (photo?.base64) {
//             sendFrame(photo.base64);
//           }
//         } catch (err) {
//           console.log("Frame capture error:", err);
//         }

//         await new Promise((r) => setTimeout(r, 500));
//       }
//     };

//     captureLoop();

//     return () => {
//       isActive = false;
//       setIsCapturing(false);
//     };
//   }, [isInitialized, permission?.granted]);

//   if (!isInitialized) {
//     return (
//       <View style={styles.loadingContainer}>
//         <ActivityIndicator size="large" color="#4CAF50" />
//         <Text style={styles.loadingText}>Initializing camera...</Text>
//       </View>
//     );
//   }

//   if (!permission?.granted) {
//     return (
//       <View style={styles.loadingContainer}>
//         <Text style={styles.loadingText}>Camera unavailable</Text>
//         <Text style={styles.loadingSubtext}>
//           Allow camera access once in Chromium.
//         </Text>
//       </View>
//     );
//   }

//   return (
//     <View style={styles.container}>
//       <ExpoCameraView
//         ref={cameraRef}
//         style={styles.camera}
//         facing="front"
//         mute={true}
//       />

//       <View style={styles.statusIndicator}>
//         <View style={[styles.statusDot, isCapturing && styles.statusDotActive]} />
//         <Text style={styles.statusText}>
//           {isCapturing ? "Capturing..." : "Idle"}
//         </Text>
//       </View>
//     </View>
//   );
// }

// const styles = StyleSheet.create({
//   container: {
//     flex: 1,
//     backgroundColor: "#000",
//   },
//   camera: {
//     flex: 1,
//   },
//   loadingContainer: {
//     flex: 1,
//     justifyContent: "center",
//     alignItems: "center",
//     backgroundColor: "#f5f5f5",
//     padding: 20,
//   },
//   loadingText: {
//     marginTop: 16,
//     fontSize: 18,
//     color: "#333",
//     fontWeight: "600",
//     textAlign: "center",
//   },
//   loadingSubtext: {
//     marginTop: 8,
//     fontSize: 14,
//     color: "#666",
//     textAlign: "center",
//   },
//   statusIndicator: {
//     position: "absolute",
//     top: 10,
//     right: 10,
//     flexDirection: "row",
//     alignItems: "center",
//     backgroundColor: "rgba(0,0,0,0.6)",
//     paddingHorizontal: 12,
//     paddingVertical: 6,
//     borderRadius: 20,
//   },
//   statusDot: {
//     width: 8,
//     height: 8,
//     borderRadius: 4,
//     backgroundColor: "#ff4444",
//     marginRight: 6,
//   },
//   statusDotActive: {
//     backgroundColor: "#44ff44",
//   },
//   statusText: {
//     color: "#fff",
//     fontSize: 12,
//     fontWeight: "600",
//   },
// });
import React, { useEffect, useRef, useState } from "react";
import { Platform, StyleSheet, Text, View, ActivityIndicator } from "react-native";
import { sendFrame } from "../services/socket";

export default function CameraView() {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const [isInitialized, setIsInitialized] = useState(false);
  const [isCapturing, setIsCapturing] = useState(false);
  const [errorText, setErrorText] = useState("");

  useEffect(() => {
    let active = true;
    let stream: MediaStream | null = null;

    const initWebCamera = async () => {
      try {
        if (
          typeof navigator === "undefined" ||
          !navigator.mediaDevices ||
          !navigator.mediaDevices.getUserMedia
        ) {
          throw new Error("mediaDevices.getUserMedia is not available");
        }

        const devices = await navigator.mediaDevices.enumerateDevices();
        console.log("MEDIA DEVICES:", devices);

        const media = await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: false,
        });

        stream = media;

        if (videoRef.current) {
          videoRef.current.srcObject = media;
          await videoRef.current.play();
        }

        if (active) {
          setErrorText("");
          setIsInitialized(true);
        }
      } catch (err: any) {
        console.error("Web camera error:", err);
        if (active) {
          setErrorText(String(err?.message || err));
          setIsInitialized(true);
        }
      }
    };

    if (Platform.OS === "web") {
      initWebCamera();
    } else {
      setErrorText("This component is intended for web on Raspberry Pi.");
      setIsInitialized(true);
    }

    return () => {
      active = false;
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  useEffect(() => {
    if (!isInitialized || Platform.OS !== "web" || errorText) return;

    let active = true;
    setIsCapturing(true);

    const loop = async () => {
      while (active) {
        try {
          const video = videoRef.current;
          const canvas = canvasRef.current;
          const ctx = canvas?.getContext("2d");

          if (video && canvas && ctx && video.videoWidth > 0 && video.videoHeight > 0) {
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

            const dataUrl = canvas.toDataURL("image/jpeg", 0.7);
            const base64 = dataUrl.split(",")[1];

            if (base64) {
              sendFrame(base64);
            }
          }
        } catch (err: any) {
          console.log("Frame capture error:", err);
          setErrorText(String(err?.message || err));
        }

        await new Promise((r) => setTimeout(r, 500));
      }
    };

    loop();

    return () => {
      active = false;
      setIsCapturing(false);
    };
  }, [isInitialized, errorText]);

  if (!isInitialized) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#4CAF50" />
        <Text style={styles.loadingText}>Initializing camera...</Text>
      </View>
    );
  }

  if (errorText) {
    return (
      <View style={styles.loadingContainer}>
        <Text style={styles.loadingText}>Camera unavailable</Text>
        <Text style={styles.errorText}>{errorText}</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        style={styles.webVideo as any}
      />
      <canvas ref={canvasRef} style={{ display: "none" }} />

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
    position: "relative",
  },
  webVideo: {
    width: "100%",
    height: "100%",
    objectFit: "cover",
    backgroundColor: "#000",
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
  errorText: {
    marginTop: 10,
    fontSize: 14,
    color: "red",
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