import { STT_URL } from "../backend/src/config";

export async function sendAudioForSTT(uri: string): Promise<string> {
  console.log("🎤 Uploading audio:", uri);

  const formData = new FormData();
  formData.append("file", {
    uri,
    name: "audio.m4a",
    type: "audio/mp4",
  } as any);

  const res = await fetch(STT_URL, {
    method: "POST",
    body: formData,
  });

  const textBody = await res.text();

  try {
    const json = JSON.parse(textBody);
    return json.text ?? "";
  } catch {
    return textBody;
  }
}
