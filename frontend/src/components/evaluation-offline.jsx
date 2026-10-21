"use client";

import React, { useState } from "react";

import {
  GENERATION_METRICS,
  RETRIEVAL_METRICS,
  runs,
  findRun,
} from "../app/evaluation/runs/index.js";

const LOW_FAITHFULNESS_THRESHOLD = 0.5;

/**
 * 0〜1のスコアを小数3桁の文字列へ整形する。欠損はダッシュを返す。
 *
 * @param {number | null | undefined} value - スコア。nullやundefinedは未計測を表す。
 * @returns {string} 小数第3位までの文字列、または「—」。
 */
function formatScore(value) {
  return typeof value === "number" ? value.toFixed(3) : "—";
}

/**
 * スコア差分を符号付き小数3桁へ整形する。
 *
 * @param {number} delta - target−baselineの差分。
 * @returns {string} 符号付きの差分文字列。
 */
function formatDelta(delta) {
  const sign = delta > 0 ? "+" : "";
  return `${sign}${delta.toFixed(3)}`;
}

/**
 * 0〜1のスコアを棒グラフの幅に使う百分率文字列へ変換する。
 *
 * @param {number} value - スコア。0未満や1超は0〜100%へ丸める。
 * @returns {string} CSSのwidthへ渡す百分率文字列。
 */
function toBarWidth(value) {
  return `${Math.min(100, Math.max(0, value * 100))}%`;
}

/**
 * ISO日時文字列を年月日時分までのUTC表記へ整形する。
 *
 * @param {string | null} isoTimestamp - 評価実行時刻のISO 8601文字列。nullは未記録。
 * @returns {string} 読みやすいUTC表記、または「—」。
 */
function formatTimestamp(isoTimestamp) {
  if (!isoTimestamp) return "—";
  const parsed = new Date(isoTimestamp);
  if (Number.isNaN(parsed.getTime())) return isoTimestamp;
  return `${parsed.toISOString().slice(0, 16).replace("T", " ")} UTC`;
}

/**
 * プルダウンの選択肢を実行日時ベースの表示名にする。同日時の区別に検索モードを併記する。
 *
 * @param {object} run - 正規化run。generatedAtとmodeを使う。
 * @returns {string} 実行日時を主とした表示名。
 */
function runOptionLabel(run) {
  const when = formatTimestamp(run.generatedAt);
  return run.mode ? `${when}・${run.mode}` : when;
}

/**
 * コード版と未コミット差分の記録を、再現性の観点で読める文字列へ整形する。
 *
 * @param {string | null} sha - 実行時のgitコミットSHA。nullは未記録。
 * @param {boolean | null} dirty - 実行時に未コミット変更があったか。nullは未記録。
 * @returns {string} SHA短縮形とdirty状態、または「—（記録なし）」。
 */
function formatCodeVersion(sha, dirty) {
  if (!sha) return "—（記録なし）";
  const short = sha.slice(0, 10);
  if (dirty === null) return short;
  return dirty ? `${short}（dirty: 再現不可）` : `${short}（clean）`;
}

/**
 * 指標名・値・意味を、数値と補助的な棒グラフで表示する。
 *
 * @param {{label: string, value: number, note: string}} props - 指標のラベル、スコア、意味の説明。
 * @returns {import("react").ReactElement} 指標カード。
 */
function MetricCard({ label, value, note }) {
  const isLowFaithfulness =
    label === "Faithfulness" && value < LOW_FAITHFULNESS_THRESHOLD;
  return (
    <div className="metric-card">
      <div className="metric-head">
        <span className="metric-label">{label}</span>
        <span className="metric-value">{formatScore(value)}</span>
      </div>
      <div className="metric-bar" aria-hidden="true">
        <span
          className={isLowFaithfulness ? "metric-bar-fill low" : "metric-bar-fill"}
          style={{ width: toBarWidth(value) }}
        />
      </div>
      <p className="metric-note">{note}</p>
    </div>
  );
}

/**
 * 選択runの実行条件を、コード版・データセット版を含めて表示する。
 *
 * @param {{run: object}} props - 表示する正規化run。
 * @returns {import("react").ReactElement} 実行条件の定義リスト。
 */
function RunExecution({ run }) {
  const fields = [
    { label: "評価ケース数", value: run.caseCount },
    { label: "実行日時", value: formatTimestamp(run.generatedAt) },
    { label: "検索方式", value: run.backend ?? "—" },
    { label: "検索モード", value: run.mode ?? "—" },
    { label: "Index", value: run.indexName ?? "—" },
    { label: "回答モデル", value: run.answerModel ?? "—" },
    { label: "RAGAS版", value: run.ragasVersion ?? "—" },
    { label: "コード版（SHA / dirty）", value: formatCodeVersion(run.codeSha, run.codeDirty) },
    { label: "データセット版", value: run.datasetVersion ?? "—（記録なし）" },
  ];
  return (
    <dl className="exec-grid">
      {fields.map((field) => (
        <div key={field.label}>
          <dt>{field.label}</dt>
          <dd>{field.value}</dd>
        </div>
      ))}
    </dl>
  );
}

/**
 * 2つのrunの共通指標について、target−baselineの差分を表で示す。
 *
 * @param {{baseline: object, target: object}} props - 比較の基準runと対象run。
 * @returns {import("react").ReactElement} 指標差分テーブル。
 */
function RunComparison({ baseline, target }) {
  const rows = [];
  for (const metric of RETRIEVAL_METRICS) {
    const base = baseline.retrievalMacro?.[metric.key];
    const next = target.retrievalMacro?.[metric.key];
    if (typeof base === "number" && typeof next === "number") {
      rows.push({ key: metric.key, group: "検索", base, next });
    }
  }
  for (const metric of GENERATION_METRICS) {
    const base = baseline.generationMacro?.[metric.key];
    const next = target.generationMacro?.[metric.key];
    if (typeof base === "number" && typeof next === "number") {
      rows.push({ key: metric.key, group: "生成", base, next });
    }
  }

  return (
    <div className="table-scroll">
      <table className="eval-table">
        <thead>
          <tr>
            <th scope="col">指標</th>
            <th scope="col">系統</th>
            <th scope="col">基準</th>
            <th scope="col">対象</th>
            <th scope="col">差分</th>
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={5}>共通して比較できる指標がありません。</td>
            </tr>
          ) : (
            rows.map((row) => {
              const delta = row.next - row.base;
              const deltaClass =
                delta > 0.0005
                  ? "delta-up"
                  : delta < -0.0005
                    ? "delta-down"
                    : undefined;
              return (
                <tr key={`${row.group}-${row.key}`}>
                  <th scope="row">{row.key}</th>
                  <td>{row.group}</td>
                  <td>{formatScore(row.base)}</td>
                  <td>{formatScore(row.next)}</td>
                  <td className={deltaClass}>{formatDelta(delta)}</td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}

/**
 * オフライン評価（自作ゴールデンセット）のrun履歴・比較・詳細を表示する。
 *
 * runの選択、2runの指標差分比較、選択runのマクロ平均・接地低下例・ケース別結果を扱う。
 * 表示データは同梱JSONの実測runで、単一runのスナップショットである。
 *
 * @returns {import("react").ReactElement} オフライン評価ワークスペース。
 */
export default function EvaluationOffline() {
  const [detailId, setDetailId] = useState(runs[0].id);
  const [baselineId, setBaselineId] = useState(
    runs[runs.length - 1].id,
  );
  const [targetId, setTargetId] = useState(runs[1] ? runs[1].id : runs[0].id);

  const detail = findRun(detailId);
  const baseline = findRun(baselineId);
  const target = findRun(targetId);
  const lowFaithfulnessCases = detail.generationMacro
    ? [...detail.cases]
        .filter((item) => item.recall >= 1 && typeof item.faithfulness === "number")
        .sort((a, b) => a.faithfulness - b.faithfulness)
        .slice(0, 5)
    : [];

  return (
    <>
      <div className="wip-banner" role="note">
        <span className="wip-tag">改善中</span>
        <span>このRAG評価ビューは現在改善中です。表示項目・指標・比較軸は今後変わる可能性があります。</span>
      </div>
      <p className="eyebrow">OFFLINE EVALUATION</p>
      <h1>RAG品質の実測記録</h1>
      <p className="lead">
        自作の評価ケース（ゴールデンセット）に対し、Azure検索・OpenAI回答生成・RAGAS判定を実行した実測値です。
        版を変えたときに品質がどう動くかを、run単位で比較できます。
      </p>

      <aside className="eval-disclaimer" aria-label="この評価の前提と限界">
        <h2>読む前に（前提と限界）</h2>
        <ul>
          <li>
            <strong>開発者が付与した自作のゴールデンセット</strong>を基準にするのは、検索5指標（Recall@k /
            Precision@k / HitRate@k / MRR@k / nDCG@k）とContextPrecision /
            ContextRecallです。外部ベンチマークではなく、値の妥当性はラベルの質に依存します。
          </li>
          <li>
            FaithfulnessとAnswerRelevancyは<strong>正解ラベルを使わず</strong>、回答・根拠・質問だけをLLMが判定します。
          </li>
          <li>
            生成4指標はRAGASのLLM判定のため<strong>run間で値が揺れます</strong>。各runは単一実行のスナップショットです。
          </li>
          <li>
            Precision@kは「正解1〜数件に対しk件返す」設計上、低めに出ます。取りこぼしはRecall@k / HitRate@kで見てください。
          </li>
          <li>合否の自動判定ではなく、改善の方向を示す記録として提示します。</li>
        </ul>
      </aside>

      <section aria-labelledby="compare-heading">
        <h2 id="compare-heading">実行日時で品質を比較（時系列）</h2>
        <p className="section-note">
          2つの実行日時の共通指標の差分を見ます。検索器の変更などによる品質の動きを追う用途です。差分は比較先−比較元で、正が改善方向です。
        </p>
        <div className="run-picker">
          <label>
            比較元（実行日時）
            <select
              value={baselineId}
              onChange={(event) => setBaselineId(event.target.value)}
            >
              {runs.map((run) => (
                <option key={run.id} value={run.id}>
                  {runOptionLabel(run)}
                </option>
              ))}
            </select>
          </label>
          <label>
            比較先（実行日時）
            <select
              value={targetId}
              onChange={(event) => setTargetId(event.target.value)}
            >
              {runs.map((run) => (
                <option key={run.id} value={run.id}>
                  {runOptionLabel(run)}
                </option>
              ))}
            </select>
          </label>
        </div>
        <RunComparison baseline={baseline} target={target} />
      </section>

      <section aria-labelledby="detail-heading">
        <h2 id="detail-heading">選択した実行日時の詳細</h2>
        <div className="run-picker">
          <label>
            表示する実行日時
            <select
              value={detailId}
              onChange={(event) => setDetailId(event.target.value)}
            >
              {runs.map((run) => (
                <option key={run.id} value={run.id}>
                  {runOptionLabel(run)}
                </option>
              ))}
            </select>
          </label>
        </div>

        <RunExecution run={detail} />

        <h3 className="subhead">検索品質（マクロ平均）</h3>
        <div className="metric-grid">
          {RETRIEVAL_METRICS.map((metric) =>
            typeof detail.retrievalMacro?.[metric.key] === "number" ? (
              <MetricCard
                key={metric.key}
                label={metric.key}
                value={detail.retrievalMacro[metric.key]}
                note={metric.note}
              />
            ) : null,
          )}
        </div>

        {detail.generationMacro ? (
          <>
            <h3 className="subhead">生成品質（マクロ平均 / RAGAS）</h3>
            <div className="metric-grid">
              {GENERATION_METRICS.map((metric) =>
                typeof detail.generationMacro[metric.key] === "number" ? (
                  <MetricCard
                    key={metric.key}
                    label={metric.key}
                    value={detail.generationMacro[metric.key]}
                    note={metric.note}
                  />
                ) : null,
              )}
            </div>
          </>
        ) : (
          <p className="section-note">
            このrunは検索のみの評価です。生成指標（RAGAS）は含みません。
          </p>
        )}

        {lowFaithfulnessCases.length > 0 ? (
          <>
            <h3 className="subhead">注目：検索は当てたが接地が落ちた例</h3>
            <p className="section-note">
              次のケースはRecall@k=1.0（正解要件を取得済み）なのにFaithfulnessが低く、改善対象が「検索」ではなく「生成時の接地」であることを示します。
            </p>
            <div className="failure-grid">
              {lowFaithfulnessCases.map((item) => (
                <article key={item.caseId} className="failure-card">
                  <div className="failure-head">
                    <span className="requirement-id">{item.caseId}</span>
                    <span className="level-badge">{item.theme}</span>
                  </div>
                  <dl className="failure-metrics">
                    <div>
                      <dt>Faithfulness</dt>
                      <dd className="low">{formatScore(item.faithfulness)}</dd>
                    </div>
                    <div>
                      <dt>AnswerRelevancy</dt>
                      <dd>{formatScore(item.answerRelevancy)}</dd>
                    </div>
                    <div>
                      <dt>Recall@k</dt>
                      <dd>{formatScore(item.recall)}</dd>
                    </div>
                  </dl>
                </article>
              ))}
            </div>
          </>
        ) : null}

        <h3 className="subhead">ケース別の実測値</h3>
        <div className="table-scroll">
          <table className="eval-table">
            <thead>
              <tr>
                <th scope="col">ケース</th>
                <th scope="col">テーマ</th>
                <th scope="col">Recall@k</th>
                <th scope="col">nDCG@k</th>
                <th scope="col">Faithfulness</th>
                <th scope="col">AnswerRelevancy</th>
              </tr>
            </thead>
            <tbody>
              {detail.cases.map((item) => (
                <tr key={item.caseId}>
                  <th scope="row">{item.caseId}</th>
                  <td>{item.theme}</td>
                  <td>{formatScore(item.recall)}</td>
                  <td>{formatScore(item.ndcg)}</td>
                  <td
                    className={
                      typeof item.faithfulness === "number" &&
                      item.faithfulness < LOW_FAITHFULNESS_THRESHOLD
                        ? "cell-low"
                        : undefined
                    }
                  >
                    {formatScore(item.faithfulness)}
                  </td>
                  <td>{formatScore(item.answerRelevancy)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
