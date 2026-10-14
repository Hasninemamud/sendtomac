import { fetchDmgDownloadCount } from "./github-downloads.js";

const KV_KEY = "sendtomac:downloads";

async function kv() {
  if (!process.env.KV_REST_API_URL) return null;
  const { kv: store } = await import("@vercel/kv");
  return store;
}

export async function incrementDownloadCount() {
  const store = await kv();
  if (!store) return;
  await store.incr(KV_KEY);
}

export async function getPublicDownloadCount() {
  const github = await fetchDmgDownloadCount().catch(() => 0);
  const store = await kv();
  if (!store) return github;
  const tracked = await store.get(KV_KEY);
  const n = typeof tracked === "number" ? tracked : 0;
  return Math.max(n, github);
}
