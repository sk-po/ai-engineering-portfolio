import assert from "node:assert/strict";
import test, { afterEach } from "node:test";
const originalBackendUrl = process.env.BACKEND_URL;
/** 各テスト後に接続先の環境変数を元に戻す。 */
afterEach(() => { if (originalBackendUrl === undefined) delete process.env.BACKEND_URL; else process.env.BACKEND_URL = originalBackendUrl; });
import { POST } from "../src/app/api/v1/requirements/search/route.js";
import { POST as postAnswer } from "../src/app/api/v1/requirements/answer/route.js";

/** テスト用のRequestを返す。bodyは省略時に既定の検索条件を使う。 */
function request(body = JSON.stringify({ query: "認証", level: 2, limit: 5 })) {
  return new Request("http://localhost/api/v1/requirements/search", { method: "POST", body });
}

test("proxy preserves request and upstream status", async (t) => {
  process.env.BACKEND_URL = "http://backend:8000";
  t.mock.method(globalThis, "fetch", async (url, options) => {
    assert.equal(url.href, "http://backend:8000/api/v1/requirements/search");
    assert.deepEqual(JSON.parse(options.body), { query: "認証", level: 2, limit: 5 });
    assert.deepEqual(options.headers, { "Content-Type": "application/json" });
    assert.equal(options.cache, "no-store");
    return Response.json({ detail: "unavailable" }, { status: 503 });
  });
  const response = await POST(request());
  assert.equal(response.status, 503);
  assert.deepEqual(await response.json(), { detail: "unavailable" });
});

test("missing config and connection failure are controlled", async (t) => {
  process.env.BACKEND_URL = "";
  assert.equal((await POST(request())).status, 503);
  process.env.BACKEND_URL = "http://backend:8000";
  t.mock.method(globalThis, "fetch", async () => { throw new Error("private connection details"); });
  const response = await POST(request());
  assert.equal(response.status, 502);
  assert.deepEqual(await response.json(), { detail: "Backend request failed" });
});

test("oversized request never reaches backend", async (t) => {
  process.env.BACKEND_URL = "http://backend:8000";
  const fetchMock = t.mock.method(globalThis, "fetch", async () => Response.json({}));
  assert.equal((await POST(request("x".repeat(65537)))).status, 413);
  assert.equal(fetchMock.mock.callCount(), 0);
});

test("successful response remains unchanged", async (t) => {
  process.env.BACKEND_URL = "http://backend:8000";
  const payload = { results: [], translation_notice: "邦訳ドラフト" };
  t.mock.method(globalThis, "fetch", async () => Response.json(payload));
  const response = await POST(request());
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), payload);
});

test("answer proxy targets the backend answer endpoint", async (t) => {
  process.env.BACKEND_URL = "http://backend:8000";
  t.mock.method(globalThis, "fetch", async (url, options) => {
    assert.equal(url.href, "http://backend:8000/api/v1/requirements/answer");
    assert.deepEqual(JSON.parse(options.body), {
      query: "認証",
      level: 2,
      limit: 5,
    });
    return Response.json({ answer: "回答", sources: [] });
  });

  const response = await postAnswer(request());
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { answer: "回答", sources: [] });
});
