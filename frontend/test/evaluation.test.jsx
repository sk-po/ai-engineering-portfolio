import "./dom-setup.js";
import React from "react";
import assert from "node:assert/strict";
import { afterEach, test } from "node:test";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import EvaluationOffline from "../src/components/evaluation-offline.jsx";
import EvaluationOnline from "../src/components/evaluation-online.jsx";
import { runs } from "../src/app/evaluation/runs/index.js";

afterEach(cleanup);

/**
 * 「ケース」列を持つケース別テーブルを取得する。比較テーブルと区別するために使う。
 *
 * @returns {HTMLElement} ケース別の実測値テーブル。
 */
function getCaseTable() {
  const tables = screen.getAllByRole("table");
  const caseTable = tables.find((table) =>
    within(table)
      .queryAllByRole("columnheader")
      .some((header) => header.textContent === "ケース"),
  );
  assert.ok(caseTable, "ケース別テーブルが見つからない");
  return caseTable;
}

test("オフライン評価が見出しと前提・限界を表示する", () => {
  render(<EvaluationOffline />);
  assert.ok(screen.getByRole("heading", { name: /RAG品質の実測記録/ }));
  const disclaimer = screen.getByRole("complementary", {
    name: "この評価の前提と限界",
  });
  assert.match(within(disclaimer).getByText(/ゴールデンセット/).textContent, /自作/);
  assert.match(disclaimer.textContent, /run間で値が揺れ/);
});

test("既定runのケース別テーブルが全ケースを行として表示する", () => {
  render(<EvaluationOffline />);
  const caseTable = getCaseTable();
  const bodyRows = within(caseTable)
    .getAllByRole("row")
    .filter((row) => within(row).queryAllByRole("columnheader").length === 0);
  assert.equal(bodyRows.length, runs[0].caseCount);
  assert.ok(within(caseTable).getAllByText(runs[0].cases[0].caseId).length > 0);
});

test("run比較がCSV→Azureの検索指標差分を示す", () => {
  render(<EvaluationOffline />);
  const azure = runs.find((run) => run.id === "retrieval-azure-51");
  const csv = runs.find((run) => run.id === "retrieval-csv-51");
  const delta = azure.retrievalMacro["Recall@k"] - csv.retrievalMacro["Recall@k"];
  const expected = `+${delta.toFixed(3)}`;
  assert.ok(screen.getAllByText(expected).length > 0);
});

test("詳細runを検索のみのrunへ切り替えると生成指標の非対象を明示する", () => {
  render(<EvaluationOffline />);
  const detailSelect = screen.getByLabelText("表示する実行日時");
  fireEvent.change(detailSelect, { target: { value: "retrieval-csv-51" } });
  assert.match(
    screen.getByText(/このrunは検索のみの評価です/).textContent,
    /生成指標（RAGAS）は含みません/,
  );
});

test("オンライン評価は未計測の設計ビューで、正解ラベル不要のシグナル源を示す", () => {
  render(<EvaluationOnline />);
  assert.ok(screen.getByRole("heading", { name: /本番トラフィックの監視と還流/ }));
  assert.match(screen.getByText(/Recall@k/).textContent, /計算できません/);
  assert.ok(screen.getByRole("heading", { name: /設計のみ（未計測）/ }));
  assert.ok(screen.getAllByText("未計測").length > 0);
});
