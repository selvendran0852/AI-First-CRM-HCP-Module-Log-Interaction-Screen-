import axios from "axios";

const client = axios.create({
  baseURL: process.env.REACT_APP_API_BASE_URL || "http://localhost:8000",
});

export const createInteraction = (payload) => client.post("/api/interactions", payload).then((r) => r.data);

export const updateInteraction = (id, payload) =>
  client.patch(`/api/interactions/${id}`, payload).then((r) => r.data);

export const searchHcps = (q) => client.get("/api/hcps", { params: { q } }).then((r) => r.data);

export const sendChatMessage = (sessionId, message) =>
  client.post("/api/chat", { session_id: sessionId, message }).then((r) => r.data);

export default client;
