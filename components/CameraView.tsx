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

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const [isCapturing, setIsCapturing] = useState(false);
  const [isInitialized, setIsInitialized] = useState(false);
  const [errorText, setErrorText] = useState("");

  useEffect(() => {
    let active = true;
    let stream: MediaStream | null = null;

    const initWebCamera = async () => {
      try {
        const media = await navigator.mediaDevices.getUserMedia({
          video: {
            width: 640,
            height: 480,
          },
          audio: false,
        });

        stream = media;

        if (videoRef.current) {
          videoRef.current.srcObject = media;
          await videoRef.current.play();
        }

        if (active) setIsInitialized(true);
      } catch (err: any) {
        console.error("Web camera error:", err);
        if (active) {
          setErrorText(String(err?.message || err));
          setIsInitialized(true);
        }
      }
    };

    const initNativeCamera = async () => {
      try {
        if (permission?.granted === true) {
          if (active) setIsInitialized(true);
          return;
        }

        if (permission?.canAskAgain !== false) {
          await requestPermission();
        }

        if (active) setIsInitialized(true);
      } catch (err: any) {
        console.error("Native camera error:", err);
        if (active) {
          setErrorText(String(err?.message || err));
          setIsInitialized(true);
        }
      }
    };

    if (Platform.OS === "web") {
      initWebCamera();
    } else {
      initNativeCamera();
    }

    return () => {
      active = false;
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
    };
  }, [permission, requestPermission]);

  useEffect(() => {
    if (!isInitialized) return;

    let isActive = true;
    setIsCapturing(true);

    const webLoop = async () => {
      while (isActive) {
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
          console.log("Web frame capture error:", err);
          setErrorText(String(err?.message || err));
        }

        await new Promise((r) => setTimeout(r, 500));
      }
    };

    const nativeLoop = async () => {
      if (!permission?.granted) return;

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
        } catch (err: any) {
          console.log("Native frame capture error:", err);
          setErrorText(String(err?.message || err));
        }

        await new Promise((r) => setTimeout(r, 500));
      }
    };

    if (Platform.OS === "web") {
      webLoop();
    } else if (permission?.granted) {
      nativeLoop();
    }

    return () => {
      isActive = false;
      setIsCapturing(false);
    };
  }, [isInitialized, permission?.granted]);

  if (!isInitialized) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#4CAF50" />
        <Text style={styles.loadingText}>Initializing camera...</Text>
      </View>
    );
  }

  if (Platform.OS !== "web" && !permission?.granted) {
    return (
      <View style={styles.loadingContainer}>
        <Text style={styles.loadingText}>Camera unavailable</Text>
        <Text style={styles.loadingSubtext}>Allow camera access.</Text>
        {!!errorText && <Text style={styles.errorText}>{errorText}</Text>}
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {Platform.OS === "web" ? (
        <>
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            style={styles.webVideo as any}
          />
          <canvas ref={canvasRef} style={{ display: "none" }} />
        </>
      ) : (
        <ExpoCameraView
          ref={cameraRef}
          style={styles.camera}
          facing="front"
          mute={true}
        />
      )}

      <View style={styles.statusIndicator}>
        <View style={[styles.statusDot, isCapturing && styles.statusDotActive]} />
        <Text style={styles.statusText}>
          {isCapturing ? "Capturing..." : "Idle"}
        </Text>
      </View>

      {!!errorText && (
        <View style={styles.errorOverlay}>
          <Text style={styles.errorOverlayText}>{errorText}</Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#000",
    position: "relative",
  },
  camera: {
    flex: 1,
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
  loadingSubtext: {
    marginTop: 8,
    fontSize: 14,
    color: "#666",
    textAlign: "center",
  },
  errorText: {
    marginTop: 10,
    fontSize: 12,
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
  errorOverlay: {
    position: "absolute",
    left: 10,
    right: 10,
    bottom: 10,
    backgroundColor: "rgba(255,0,0,0.75)",
    padding: 8,
    borderRadius: 8,
  },
  errorOverlayText: {
    color: "#fff",
    fontSize: 12,
    textAlign: "center",
  },
});