import http from "k6/http";
import { check, sleep } from "k6";
import { Rate } from "k6/metrics";

const BASE = __ENV.BASE_URL || "https://sendtomac.vercel.app";
const failRate = new Rate("failed_requests");

export const options = {
  // ponytail: pin working Vercel edge; remove if ISP path is healthy
  hosts: { "sendtomac.vercel.app": "64.29.17.67" },
  stages: [
    { duration: "15s", target: 10 },
    { duration: "30s", target: 25 },
    { duration: "15s", target: 0 },
  ],
  thresholds: {
    http_req_failed: ["rate<0.05"],
    http_req_duration: ["p(95)<1500"],
    failed_requests: ["rate<0.05"],
  },
};

const PAGES = ["/", "/privacy", "/share"];
const ASSETS = [
  "/theme.css",
  "/theme.js",
  "/logo.png",
  "/favicon.ico",
  "/icon.svg",
];

export default function () {
  const page = PAGES[Math.floor(Math.random() * PAGES.length)];
  const pageRes = http.get(`${BASE}${page}`, {
    tags: { name: "page" },
    redirects: 5,
  });
  const pageOk = check(pageRes, {
    "page status 200": (r) => r.status === 200,
    "page has body": (r) => r.body && r.body.length > 0,
  });
  failRate.add(!pageOk);

  const asset = ASSETS[Math.floor(Math.random() * ASSETS.length)];
  const assetRes = http.get(`${BASE}${asset}`, {
    tags: { name: "asset" },
    redirects: 5,
  });
  const assetOk = check(assetRes, {
    "asset status 200": (r) => r.status === 200,
  });
  failRate.add(!assetOk);

  sleep(1);
}
