import React from "react";

// 本番トラフィックから正解ラベル無しで計測する予定のシグナル。数値はデータストア整備後に表示する。
const PLANNED_SIGNALS = [
  {
    name: "ゼロ件率",
    source: "rag_search イベントの result_count",
    needsLabel: false,
  },
  {
    name: "検索トップスコア分布",
    source: "rag_search イベントの results[].score",
    needsLabel: false,
  },
  {
    name: "レイテンシ p50 / p95",
    source: "rag_search・rag_generation の duration_ms",
    needsLabel: false,
  },
  {
    name: "引用カバレッジ",
    source: "rag_generation の source_ids と回答本文の突合",
    needsLabel: false,
  },
  {
    name: "Faithfulness / AnswerRelevancy（サンプル）",
    source: "実クエリのサンプルにRAGASをreference-free適用",
    needsLabel: false,
  },
  {
    name: "ユーザ満足度",
    source: "回答へのthumbs up/down",
    needsLabel: false,
  },
];

/**
 * オンライン評価（本番トラフィック）の設計と、計測予定シグナルを表示する。
 *
 * 正解ラベルの無い実クエリをreference-free指標・運用シグナル・人手フィードバックで監視し、
 * サンプルをゴールデンセットへ還流する設計を示す。数値はデータストア整備後に表示するため未計測。
 *
 * @returns {import("react").ReactElement} オンライン評価の設計ビュー。
 */
export default function EvaluationOnline() {
  return (
    <>
      <p className="eyebrow">ONLINE EVALUATION</p>
      <h1>本番トラフィックの監視と還流</h1>
      <p className="lead">
        実クエリには正解ラベルがないため、Recall@kなどのラベル依存指標は計算できません。
        ここでは正解ラベルを使わないシグナルで品質を監視し、弱点を見つけてゴールデンセットへ還流します。
      </p>

      <aside className="eval-disclaimer" aria-label="このビューの状態">
        <h2>状態：設計のみ（未計測）</h2>
        <ul>
          <li>
            数値表示は<strong>データストア整備後</strong>に実装します。現時点ではログを集計・永続化していないため、本ページは計測対象と設計の提示に留めます。
          </li>
          <li>
            計測は実リクエスト経路では行わず、ログ由来のバッチ集計とサンプル評価で行います（コストとレイテンシを本番に乗せない）。
          </li>
        </ul>
      </aside>

      <section aria-labelledby="signals-heading">
        <h2 id="signals-heading">計測予定のシグナル</h2>
        <p className="section-note">
          いずれも正解ラベルを必要とせず、アプリが既に出力している構造化ログ、またはユーザ操作から得られます。
        </p>
        <div className="table-scroll">
          <table className="eval-table">
            <thead>
              <tr>
                <th scope="col">シグナル</th>
                <th scope="col">データ源</th>
                <th scope="col">正解ラベル</th>
                <th scope="col">現状</th>
              </tr>
            </thead>
            <tbody>
              {PLANNED_SIGNALS.map((signal) => (
                <tr key={signal.name}>
                  <th scope="row">{signal.name}</th>
                  <td>{signal.source}</td>
                  <td>{signal.needsLabel ? "必要" : "不要"}</td>
                  <td>未計測</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section aria-labelledby="loop-heading">
        <h2 id="loop-heading">オフラインとの関係（品質改善ループ）</h2>
        <p className="section-note">
          オンラインは「次に何を直すか」を供給し、オフラインは「版を変えて改善したか」を測ります。両者は閉ループです。
        </p>
        <ol className="loop-steps">
          <li>オンラインで失敗・弱点を検知（ゼロ件・低Faithfulness・低評価）。</li>
          <li>該当クエリをサンプリングし、人手で正解要件IDを付与。</li>
          <li>ゴールデンセットへ追加し、評価セットを成長させる。</li>
          <li>オフライン評価で版ごとの品質差分を測り、改善を確認する。</li>
        </ol>
      </section>
    </>
  );
}
