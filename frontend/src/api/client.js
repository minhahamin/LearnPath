import axios from "axios";

const baseURL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const client = axios.create({ baseURL });

export async function curate(topic) {
  const { data } = await client.post("/api/curate", { topic });
  return data; // { roadmap_id }
}

export async function getRoadmap(roadmapId) {
  const { data } = await client.get(`/api/roadmaps/${roadmapId}`);
  return data;
}

export async function getRoadmapSteps(roadmapId) {
  const { data } = await client.get(`/api/roadmaps/${roadmapId}/steps`);
  return data;
}

export async function listRoadmaps() {
  const { data } = await client.get("/api/roadmaps");
  return data;
}

export async function updateProgress(roadmapId, url, completed) {
  const { data } = await client.patch(`/api/roadmaps/${roadmapId}/progress`, { url, completed });
  return data; // { progress }
}
