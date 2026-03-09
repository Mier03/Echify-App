// import { Platform } from "react-native";

// const STT_URL = "http://10.15.58.14:8000/stt";

// export async function sendAudioForSTT(uri: string): Promise<string> {
//   console.log("🎤 Uploading audio:", uri);

//   const formData = new FormData();

//   if (Platform.OS === "web") {
//     // On web, convert the recorded URI/blob URL into a real Blob
//     const fileResponse = await fetch(uri);
//     const blob = await fileResponse.blob();

//     formData.append("file", blob, "audio.webm");
//   } else {
//     // On Android/iOS, keep the React Native file object style
//     formData.append("file", {
//       uri,
//       name: "audio.m4a",
//       type: "audio/mp4",
//     } as any);
//   }

//   let res: Response;

//   try {
//     res = await fetch(STT_URL, {
//       method: "POST",
//       body: formData,
//     });
//   } catch (e) {
//     console.log("❌ fetch failed:", e);
//     throw e;
//   }

//   console.log("✅ STT status:", res.status);

//   const textBody = await res.text();
//   console.log("✅ STT raw body:", textBody);

//   try {
//     const json = JSON.parse(textBody);
//     return json.text ?? "";
//   } catch {
//     return textBody;
//   }
// }
// services/stt.ts
import { Platform } from "react-native";

const getSttUrl = () => {
  if (typeof window !== "undefined" && window.location?.hostname) {
    return `http://${window.location.hostname}:8000/stt`;
  }
  return "http://localhost:8000/stt";
};

export async function sendAudioForSTT(input: string | Blob): Promise<string> {
  console.log("🎤 Uploading audio:", input);

  const formData = new FormData();

  if (Platform.OS === "web") {
    let blob: Blob;

    if (input instanceof Blob) {
      blob = input;
    } else {
      const fileResponse = await fetch(input);
      blob = await fileResponse.blob();
    }

    formData.append("file", blob, "audio.webm");
  } else {
    formData.append("file", {
      uri: input as string,
      name: "audio.m4a",
      type: "audio/mp4",
    } as any);
  }

  const STT_URL = getSttUrl();

  let res: Response;

  try {
    res = await fetch(STT_URL, {
      method: "POST",
      body: formData,
    });
  } catch (e) {
    console.log("❌ fetch failed:", e);
    throw e;
  }

  console.log("✅ STT status:", res.status);

  const textBody = await res.text();
  console.log("✅ STT raw body:", textBody);

  try {
    const json = JSON.parse(textBody);
    return json.text ?? "";
  } catch {
    return textBody;
  }
}