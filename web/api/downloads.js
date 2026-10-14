import { getPublicDownloadCount } from "../lib/download-count.js";

export default async function handler(_req, res) {
  try {
    const count = await getPublicDownloadCount();
    res.setHeader("Cache-Control", "public, s-maxage=120, stale-while-revalidate=300");
    res.status(200).json({ count });
  } catch {
    res.status(200).json({ count: null });
  }
}
