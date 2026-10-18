import { rawRuns } from "./manifest.js";

// 検索指標のsnake_caseキーを、画面表示で使うLabel@k表記へ対応付ける。
const RETRIEVAL_KEY_MAP = {
  recall_at_k: "Recall@k",
  precision_at_k: "Precision@k",
  hit_rate_at_k: "HitRate@k",
  mrr_at_k: "MRR@k",
  ndcg_at_k: "nDCG@k",
};

export const RETRIEVAL_METRICS = [
  { key: "Recall@k", note: "正解要件のうち上位k件で取得できた割合" },
  { key: "Precision@k", note: "上位k件に占める正解の割合。正解数に対しkが大きいほど下がる" },
  { key: "HitRate@k", note: "少なくとも1件の正解を取得できたケースの割合" },
  { key: "MRR@k", note: "最初の正解が現れた順位の逆数。上位に出すほど高い" },
  { key: "nDCG@k", note: "正解の順位を考慮した取得品質" },
];

export const GENERATION_METRICS = [
  { key: "Faithfulness", note: "回答が渡した根拠だけに基づくか（接地）。正解ラベルは使わない" },
  { key: "AnswerRelevancy", note: "回答が質問の焦点に答えているか。正解ラベルは使わない" },
  { key: "ContextPrecision", note: "渡した根拠のうち回答に有用だった割合。正解から作る参照回答が基準" },
  { key: "ContextRecall", note: "参照回答の内容を根拠が網羅していたか。正解から作る参照回答が基準" },
];

/**
 * 検索指標をsnake_caseまたはLabel@k表記のどちらからでもLabel@k辞書へ正規化する。
 *
 * @param {Record<string, number> | undefined} metrics - 検索指標の辞書。snake_caseまたはLabel@kキー。
 * @returns {Record<string, number> | null} Label@kをキーとする辞書。入力が無い場合はnull。
 */
function normalizeRetrieval(metrics) {
  if (!metrics) return null;
  if ("Recall@k" in metrics) return metrics;
  const normalized = {};
  for (const [snakeKey, label] of Object.entries(RETRIEVAL_KEY_MAP)) {
    if (snakeKey in metrics) normalized[label] = metrics[snakeKey];
  }
  return normalized;
}

/**
 * 検索専用runとRAGAS統合runの両スキーマを、画面共通の正規化runへ変換する。
 *
 * @param {{id: string, label: string, raw: object}} params - run識別子、表示名、読み込んだ評価JSON。
 * @returns {object} マクロ平均・ケース別・実行条件を共通形で持つ正規化run。
 */
function normalizeRun({ id, label, raw }) {
  const execution = raw.execution ?? {};
  const nested = Boolean(raw.macro_average && raw.macro_average.retrieval);
  const retrievalMacro = normalizeRetrieval(
    nested ? raw.macro_average.retrieval : raw.macro_average,
  );
  const generationMacro = nested ? raw.macro_average.generation : null;
  const cases = raw.cases.map((item) => {
    const retrieval = normalizeRetrieval(
      item.retrieval ? item.retrieval.metrics : item.metrics,
    );
    const generation = item.generation ? item.generation.metrics : null;
    return {
      caseId: item.case_id,
      theme: item.theme,
      recall: retrieval ? retrieval["Recall@k"] : null,
      ndcg: retrieval ? retrieval["nDCG@k"] : null,
      faithfulness: generation ? generation.Faithfulness : null,
      answerRelevancy: generation ? generation.AnswerRelevancy : null,
    };
  });
  return {
    id,
    label,
    generatedAt: raw.generated_at ?? null,
    caseCount: raw.case_count,
    backend: execution.search_backend ?? null,
    mode: execution.search_mode ?? null,
    indexName: execution.search_index_name ?? null,
    answerModel: execution.answer_model ?? null,
    ragasVersion: execution.ragas_version ?? null,
    codeSha: execution.code_sha ?? null,
    codeDirty: typeof execution.code_dirty === "boolean" ? execution.code_dirty : null,
    datasetVersion: execution.dataset_fingerprint ?? execution.dataset_version ?? null,
    retrievalMacro,
    generationMacro,
    cases,
  };
}

// 表示順は manifest.json の並び（＝publishスクリプトで管理）に従う。
export const runs = rawRuns.map(normalizeRun);

/**
 * run IDから正規化runを取得する。
 *
 * @param {string} id - 取得するrunのID。
 * @returns {object | undefined} 一致する正規化run。無ければundefined。
 */
export function findRun(id) {
  return runs.find((run) => run.id === id);
}
