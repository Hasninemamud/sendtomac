export const GITHUB_REPO = "Hasninemamud/sendtomac";
export const DMG_ASSET = "SendToMac.dmg";
export const DMG_URL =
  `https://github.com/${GITHUB_REPO}/releases/latest/download/${DMG_ASSET}`;

const RELEASE_URL = `https://api.github.com/repos/${GITHUB_REPO}/releases/latest`;

export async function fetchDmgDownloadCount() {
  const res = await fetch(RELEASE_URL, {
    headers: {
      Accept: "application/vnd.github+json",
      "User-Agent": "SendToMac-Website",
      "X-GitHub-Api-Version": "2022-11-28",
    },
  });
  if (!res.ok) {
    throw new Error(`GitHub API ${res.status}`);
  }
  const release = await res.json();
  const asset = (release.assets || []).find((a) => a.name === DMG_ASSET);
  return asset?.download_count ?? 0;
}
