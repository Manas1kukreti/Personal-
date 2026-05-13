import { useEffect } from "react";
import { websocketUrl } from "../api/client.js";

export function useWebSocket(channel, onMessage) {
  useEffect(() => {
    const socket = new WebSocket(websocketUrl(channel));
    socket.onmessage = (event) => {
      try {
        onMessage(JSON.parse(event.data));
      } catch {
        onMessage({ event: "raw", payload: event.data });
      }
    };
    return () => socket.close();
  }, [channel, onMessage]);
}
