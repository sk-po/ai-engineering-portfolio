export const RETRIEVAL_LIMIT_PER_LEVEL = 5;

/**
 * 要件APIへ送る質問を前後空白除去し、最低文字数を検証する。
 *
 * @param {string} query - 利用者が入力した質問。前後空白除去後に2文字以上必要。
 * @returns {string} 前後空白を除去した質問。
 * @throws {Error} 正規化後の質問が2文字未満の場合。
 */
function normalizeQuery(query) {
  const normalizedQuery = query.trim();
  if (normalizedQuery.length < 2) {
    throw new Error("質問を2文字以上入力してください。");
  }
  return normalizedQuery;
}

/**
 * 検索条件を送信して関連要件を返す。
 *
 * @param {{query: string, level?: number}} conditions - 質問と最上位Level。L1から指定Levelまでを各5件抽出する。
 * @param {typeof fetch} fetchImplementation - 通信処理。テスト時の差し替え用で、省略時はブラウザのfetch。
 * @returns {Promise<object>} バックエンドが返した検索結果。
 * @throws {Error} 質問が短い場合、またはAPIが成功以外を返した場合。
 */
export async function searchRequirements(
  { query, level = 2 },
  fetchImplementation = fetch,
) {
  const normalizedQuery = normalizeQuery(query);

  const response = await fetchImplementation("/api/v2/requirements/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query: normalizedQuery, level }),
  });

  if (!response.ok) {
    throw new Error("検索に失敗しました。バックエンドの起動状態を確認してください。");
  }

  return response.json();
}

/**
 * 質問を送信し、ASVS要件を根拠に生成された回答を返す。
 *
 * @param {{query: string, level?: number}} conditions - 質問と最上位Level。L1から指定Levelまでを各5件根拠として抽出する。
 * @param {typeof fetch} fetchImplementation - 通信処理。テスト時の差し替え用で、省略時はブラウザのfetch。
 * @returns {Promise<object>} 生成回答と、モデルへ渡された根拠要件。
 * @throws {Error} 質問が短い場合、またはAPIが成功以外を返した場合。
 */
export async function generateRequirementAnswer(
  { query, level = 2 },
  fetchImplementation = fetch,
) {
  const normalizedQuery = normalizeQuery(query);
  const response = await fetchImplementation("/api/v2/requirements/answer", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query: normalizedQuery, level }),
  });

  if (!response.ok) {
    throw new Error(
      "AI回答の生成に失敗しました。バックエンドの設定と起動状態を確認してください。",
    );
  }

  return response.json();
}

/**
 * ガイド付き要件探索を1ターン進める。
 *
 * @param {{featureDescription: string, answers: string[], level: number}} conditions - 機能説明、これまでの回答、ASVS最上位Level。
 * @param {typeof fetch} fetchImplementation - 通信処理。テスト時の差し替え用で、省略時はブラウザのfetch。
 * @returns {Promise<object>} 次の質問または根拠付き最終回答。
 */
export async function guideRequirements(
  { featureDescription, answers, level = 2 },
  fetchImplementation = fetch,
) {
  const response = await fetchImplementation("/api/v2/guided-requirements/turn", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ feature_description: normalizeQuery(featureDescription), answers, level }),
  });
  if (!response.ok) {
    if (response.status === 503) {
      throw new Error("AIによる確認処理に失敗しました。少し時間を置いて同じ回答を再送してください。");
    }
    if (response.status === 422) {
      throw new Error("機能要件は20文字以上で入力してください。");
    }
    throw new Error("セキュリティレビューを続行できませんでした。バックエンドの起動状態を確認してください。");
  }
  return response.json();
}

/**
 * 数値のASVS Levelを表示用文字列へ変換する。
 *
 * @param {number} level - 1から3のASVS Level。
 * @returns {string} `Level 1`形式の表示文字列。
 */
export function formatLevel(level) {
  return `Level ${level}`;
}
