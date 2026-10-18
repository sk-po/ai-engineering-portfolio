import "./dom-setup.js";
import React from "react";
import assert from "node:assert/strict";
import { afterEach, test } from "node:test";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import SearchWorkspace from "../src/components/search-workspace.jsx";

afterEach(cleanup);

test("search results and input survive accessible tab switching", async (t) => {
  t.mock.method(globalThis, "fetch", async () => Response.json({ translation_notice: "邦訳ドラフト", results: [{ requirement_id: "V6.1.1", level: 1, score: 0.85, section_name_ja: "認証", description_ja: "公開要件", description_en: "Public requirement" }] }));
  render(<SearchWorkspace />);
  fireEvent.change(screen.getByLabelText("確認したいこと"), { target: { value: "パスワード" } });
  fireEvent.click(screen.getByRole("button", { name: "要件を検索" }));
  await screen.findByText("V6.1.1");
  fireEvent.keyDown(screen.getByRole("tab", { name: "要件検索" }), { key: "ArrowRight" });
  assert.equal(screen.getByRole("tab", { name: "AI回答" }).getAttribute("aria-selected"), "true");
  assert.ok(screen.getByRole("heading", { name: /ASVSを根拠に/ }));
  assert.ok(screen.getByRole("button", { name: "AI回答を生成" }));
  fireEvent.keyDown(screen.getByRole("tab", { name: "AI回答" }), { key: "Home" });
  assert.equal(screen.getByLabelText("確認したいこと").value, "パスワード");
  assert.ok(screen.getByText("V6.1.1"));
  assert.equal(globalThis.fetch.mock.callCount(), 1);
});

test("AI tab generates an answer and displays its exact sources", async (t) => {
  const mocked = t.mock.method(globalThis, "fetch", async (url) => {
    assert.equal(url, "/api/v2/requirements/answer");
    return Response.json({
      answer: "認証要件を文書化してください。[V6.1.1]",
      translation_notice: "邦訳ドラフト",
      sources: [
        {
          requirement_id: "V6.1.1",
          chapter_id: "V6",
          chapter_name_en: "Authentication",
          section_id: "V6.1",
          section_name_ja: "認証セキュリティ",
          section_name_en: "Authentication Security",
          description_ja: "認証要件を文書化する。",
          description_en: "Document authentication requirements.",
          level: 1,
          score: 0.85,
        },
      ],
    });
  });

  render(<SearchWorkspace />);
  fireEvent.click(screen.getByRole("tab", { name: "AI回答" }));
  fireEvent.change(screen.getByLabelText("確認したいこと"), {
    target: { value: "認証をどのように設計する？" },
  });
  fireEvent.click(screen.getByRole("button", { name: "AI回答を生成" }));

  await screen.findByText("認証要件を文書化してください。[V6.1.1]");
  assert.ok(screen.getByText("V6.1.1"));
  assert.ok(screen.getByText("認証要件を文書化する。"));
  assert.equal(mocked.mock.callCount(), 1);
  assert.deepEqual(JSON.parse(mocked.mock.calls[0].arguments[1].body), {
    query: "認証をどのように設計する？",
    level: 2,
  });
});

test("empty results and failed searches are explained", async (t) => {
  const mocked = t.mock.method(globalThis, "fetch", async () => Response.json({ results: [] }));
  render(<SearchWorkspace />);
  fireEvent.change(screen.getByLabelText("確認したいこと"), { target: { value: "認証" } });
  fireEvent.click(screen.getByRole("button", { name: "要件を検索" }));
  await screen.findByText(/関連する要件を見つけられませんでした/);
  mocked.mock.mockImplementation(async () => Response.json({}, { status: 503 }));
  fireEvent.click(screen.getByRole("button", { name: "要件を検索" }));
  await waitFor(() => assert.match(screen.getByRole("status").textContent, /検索に失敗/));
});
