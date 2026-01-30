import axios from 'axios';

const BASE = 'http://localhost:8001';

export async function health() {
  return (await axios.get(`${BASE}/health`)).data;
}
export async function account() {
  return (await axios.get(`${BASE}/account`)).data;
}
export async function positions() {
  return (await axios.get(`${BASE}/positions`)).data;
}
export async function pause() {
  return (await axios.post(`${BASE}/risk/pause`)).data;
}
export async function resume() {
  return (await axios.post(`${BASE}/risk/resume`)).data;
}
export async function flatten() {
  return (await axios.post(`${BASE}/risk/flatten`)).data;
}
