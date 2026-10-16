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

function asCount(value) {
  const n = Number(value);
  return Number.isFinite(n) && n >= 0 ? Math.floor(n) : 0;
}

export async function getPublicDownloadCount() {
  const github = await fetchDmgDownloadCount().catch(() => 0);
  const githubN = asCount(github);
  const store = await kv();
  if (!store) return githubN;
  const tracked = await store.get(KV_KEY);
  return Math.max(asCount(tracked), githubN);
}
