import assert from "node:assert/strict";
import worker from "../workers/preview-auth.mjs";

const assets = {
  fetch: async () => new Response("preview ok", { status: 200 }),
};

const denied = await worker.fetch(new Request("https://preview.example.test/"), {
  ASSETS: assets,
  PREVIEW_PASSWORD: "test-password",
});
assert.equal(denied.status, 401);
assert.match(denied.headers.get("www-authenticate"), /NewsRadar Preview/);
assert.match(denied.headers.get("x-robots-tag"), /noindex/);

const credentials = btoa("newsradar:test-password");
const allowed = await worker.fetch(
  new Request("https://preview.example.test/", {
    headers: { Authorization: `Basic ${credentials}` },
  }),
  { ASSETS: assets, PREVIEW_PASSWORD: "test-password" },
);
assert.equal(allowed.status, 200);
assert.equal(await allowed.text(), "preview ok");

const unconfigured = await worker.fetch(new Request("https://preview.example.test/"), {
  ASSETS: assets,
});
assert.equal(unconfigured.status, 503);
