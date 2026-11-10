export const GITHUB_REPO = "Hasninemamud/sendtomac";
export const DMG_ASSET = "SendToMac.dmg";
export const DMG_URL =
  `https://github.com/${GITHUB_REPO}/releases/latest/download/${DMG_ASSET}`;

// shortcut: first 100 releases only (the API's page cap), upgrade to pagination past 100 releases.
const RELEASES_URL = `https://api.github.com/repos/${GITHUB_REPO}/releases?per_page=100`;

// Downloads across every release. Old releases shipped a .zip, so count all assets except .sig signatures.
export async function fetchTotalDownloadCount() {
  const res = await fetch(RELEASES_URL, {
    headers: {
      Accept: "application/vnd.github+json",
      "User-Agent": "SendToMac-Website",
      "X-GitHub-Api-Version": "2022-11-28",
    },
  });
  if (!res.ok) {
    throw new Error(`GitHub API ${res.status}`);
  }
  const releases = await res.json();
  let total = 0;
  for (const release of releases) {
    for (const asset of release.assets || []) {
      const n = Number(asset.download_count);
      if (!asset.name.endsWith(".sig") && Number.isFinite(n) && n > 0) total += n;
    }
  }
  return total;
}
