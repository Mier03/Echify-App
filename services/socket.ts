let socket: WebSocket | null = null;
let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;

let messageCallback: ((data: any) => void) | null = null;

const getWsUrl = () => {
  const host =
    typeof window !== "undefined" ? window.location.hostname : "localhost";
  return `ws://${host}:8000/ws/fsl-simple`;
};

export const connectSocket = (onMessage: (data: any) => void) => {
  messageCallback = onMessage;

  if (socket && socket.readyState === WebSocket.OPEN) return;

  const WS_URL = getWsUrl();
  console.log("🌐 Connecting to WebSocket:", WS_URL);

  socket = new WebSocket(WS_URL);

  socket.onopen = () => {
    console.log("✅ WebSocket connected");
    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout);
      reconnectTimeout = null;
    }
  };

  socket.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      if (messageCallback) messageCallback(data);
    } catch {
      if (messageCallback) messageCallback({ prediction: String(e.data) });
    }
  };

  socket.onerror = () => console.log("❌ WebSocket error");

  socket.onclose = () => {
    console.log("🔌 WebSocket closed");
    socket = null;
    if (!reconnectTimeout) {
      reconnectTimeout = setTimeout(() => {
        reconnectTimeout = null;
        if (messageCallback) connectSocket(messageCallback);
      }, 3000);
    }
  };
};

export const sendFrame = (frameBase64: string) => {
  if (!socket || socket.readyState !== WebSocket.OPEN) return false;
  try {
    socket.send(frameBase64);
    return true;
  } catch {
    return false;
  }
};

export const closeSocket = () => {
  if (reconnectTimeout) clearTimeout(reconnectTimeout);
  reconnectTimeout = null;
  messageCallback = null;
  socket?.close();
  socket = null;
};