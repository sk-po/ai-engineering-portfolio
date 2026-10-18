import assert from "node:assert/strict";
import test from "node:test";

import {
  formatLevel,
  generateRequirementAnswer,
  searchRequirements,
} from "../src/asvs.js";

test("posts a normalized Japanese query", async () => {
  let capturedRequest;
  const fakeFetch = async (url, options) => {
    capturedRequest = { url, options };
    return {
      ok: true,
      async json() {
        return { results: [] };
      },
    };
  };

  await searchRequirements(
    { query: "  パスワード保存  ", level: 2 },
    fakeFetch,
  );

  assert.equal(capturedRequest.url, "/api/v2/requirements/search");
  assert.deepEqual(JSON.parse(capturedRequest.options.body), {
    query: "パスワード保存",
    level: 2,
  });
});

test("rejects a short query before calling the API", async () => {
  await assert.rejects(
    searchRequirements({ query: "a", level: 2 }),
    /2文字以上/,
  );
});

test("posts AI questions to the answer endpoint", async () => {
  let capturedRequest;
  const fakeFetch = async (url, options) => {
    capturedRequest = { url, options };
    return {
      ok: true,
      async json() {
        return { answer: "回答", sources: [] };
      },
    };
  };

  await generateRequirementAnswer(
    { query: "  認証をどう設計する？  ", level: 3 },
    fakeFetch,
  );

  assert.equal(capturedRequest.url, "/api/v2/requirements/answer");
  assert.deepEqual(JSON.parse(capturedRequest.options.body), {
    query: "認証をどう設計する？",
    level: 3,
  });
});

test("formats an ASVS level", () => {
  assert.equal(formatLevel(3), "Level 3");
});
