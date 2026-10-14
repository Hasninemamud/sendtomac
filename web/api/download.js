import { DMG_URL } from "../lib/github-downloads.js";
import { incrementDownloadCount } from "../lib/download-count.js";

export default async function handler(_req, res) {
  try {
    await incrementDownloadCount();
  } catch {
    /* counter is best-effort */
  }
  res.writeHead(302, { Location: DMG_URL });
  res.end();
}
