"use client";

import Link from "next/link";
import React, { useRef, useState } from "react";

import {
  formatLevel,
  generateRequirementAnswer,
  searchRequirements,
} from "../asvs.js";
import GuidedRequirementsWorkspace from "./guided-requirements-workspace.jsx";

const DEFAULT_TRANSLATION_NOTICE =
  "日本語はコミュニティ邦訳ドラフトです。正式な解釈は英語原文を確認してください。";
const IDLE_OPERATION = { phase: "idle", payload: null, error: "" };

/**
 * ASVS要件を検索結果またはAI回答の根拠として表示する。
 *
 * @param {{item: object}} props - 表示する要件。要件ID、Level、日本語・英語本文、分類、スコアを含む。
 * @returns {import("react").ReactElement} 要件カード。
 */
function RequirementCard({ item }) {
  const score =
    typeof item.score === "number" ? `スコア ${item.score.toFixed(3)}` : null;

  return (
    <article className="result-card">
      <div className="result-meta">
        <span className="requirement-id">{item.requirement_id}</span>
        <span className="level-badge">{formatLevel(item.level)}</span>
        {score ? <span className="score">{score}</span> : null}
      </div>
      <h3 className="result-title">
        {item.section_name_ja || item.section_name_en || item.requirement_id}
      </h3>
      <p className="result-description">{item.description_ja}</p>
      <details>
        <summary>英語原文と分類を確認</summary>
        <p className="english-description">{item.description_en}</p>
        <p className="source-path">
          {item.chapter_id} {item.chapter_name_en} / {item.section_id}{" "}
          {item.section_name_en}
        </p>
      </details>
    </article>
  );
}

/**
 * 要件一覧をカードとして表示する。
 *
 * @param {{requirements: object[], emptyMessage: string}} props - 表示する要件配列と、空の場合の案内文。
 * @returns {import("react").ReactElement} 要件一覧または空状態。
 */
function RequirementList({ requirements, emptyMessage }) {
  if (requirements.length === 0) {
    return <p className="empty-state">{emptyMessage}</p>;
  }

  return requirements.map((item) => (
    <RequirementCard key={item.requirement_id} item={item} />
  ));
}

/**
 * 選択Levelに応じたRAG抽出件数を画面用の文章に変換する。
 *
 * @param {{levels_searched?: number[], limit_per_level?: number} | undefined} retrieval - APIが返したLevel別の抽出条件。
 * @returns {string | null} 抽出条件を説明する文章。情報がない場合はnull。
 */
function formatRetrievalSummary(retrieval) {
  if (!retrieval?.levels_searched?.length) return null;
  const levels = retrieval.levels_searched.map((level) => `L${level}`).join("・");
  return `${levels}を個別に検索し、各Level最大${retrieval.limit_per_level}件を抽出`;
}

/**
 * 検索処理の結果領域を表示する。
 *
 * @param {{operation: {phase: string, payload: object | null, error: string}}} props - 検索の進行状態とレスポンス。
 * @returns {import("react").ReactElement} 検索結果領域。
 */
function SearchResults({ operation }) {
  const payload = operation.payload;
  const retrievalSummary = formatRetrievalSummary(payload?.retrieval);
  const statusMessage =
    operation.phase === "loading"
      ? "検索しています…"
      : operation.phase === "error"
        ? operation.error
        : payload?.translation_notice || DEFAULT_TRANSLATION_NOTICE;

  return (
    <section className="results-section" aria-labelledby="result-summary">
      <div className="results-heading">
        <h2 id="result-summary">
          {payload ? `${payload.results.length}件の関連要件` : "検索結果"}
        </h2>
        <p
          id="search-status"
          className={operation.phase === "error" ? "error" : undefined}
          role="status"
          aria-live="polite"
        >
          {statusMessage}
        </p>
      </div>
      {retrievalSummary ? <p className="retrieval-summary">{retrievalSummary}</p> : null}
      <div
        className="results"
        aria-live="polite"
        aria-busy={operation.phase === "loading"}
      >
        {operation.phase === "loading" ? (
          <p className="empty-state">関連する要件を検索しています…</p>
        ) : payload ? (
          <RequirementList
            requirements={payload.results}
            emptyMessage="関連する要件を見つけられませんでした。別の言葉で質問してください。"
          />
        ) : (
          <p className="empty-state">
            質問を入力すると、関連する要件がここに表示されます。
          </p>
        )}
      </div>
    </section>
  );
}

/**
 * AI回答と、モデルへ渡された根拠要件を表示する。
 *
 * @param {{operation: {phase: string, payload: object | null, error: string}}} props - AI回答生成の進行状態とレスポンス。
 * @returns {import("react").ReactElement} AI回答結果領域。
 */
function AnswerResults({ operation }) {
  const payload = operation.payload;
  const retrievalSummary = formatRetrievalSummary(payload?.retrieval);
  const statusMessage =
    operation.phase === "loading"
      ? "AI回答を生成しています…"
      : operation.phase === "error"
        ? operation.error
        : payload?.translation_notice || DEFAULT_TRANSLATION_NOTICE;

  return (
    <section className="results-section" aria-labelledby="answer-summary">
      <div className="results-heading">
        <h2 id="answer-summary">AI回答</h2>
        <p
          id="search-status"
          className={operation.phase === "error" ? "error" : undefined}
          role="status"
          aria-live="polite"
        >
          {statusMessage}
        </p>
      </div>
      <div
        className="results"
        aria-live="polite"
        aria-busy={operation.phase === "loading"}
      >
        {operation.phase === "loading" ? (
          <p className="empty-state">検索結果を根拠に回答を生成しています…</p>
        ) : payload ? (
          <>
            <article className="answer-card">
              <h3>生成された回答</h3>
              <p className="answer-text">{payload.answer}</p>
              <p className="answer-caveat">
                この回答はASVS適合性を保証するものではありません。
              </p>
            </article>
            <div className="source-heading">
              <h3>回答の根拠</h3>
              <span>{payload.sources.length}件</span>
            </div>
            {retrievalSummary ? (
              <p className="retrieval-summary">{retrievalSummary}</p>
            ) : null}
            <RequirementList
              requirements={payload.sources}
              emptyMessage="回答に利用できる根拠要件はありませんでした。"
            />
          </>
        ) : (
          <p className="empty-state">
            質問を入力すると、ASVS要件を根拠にした回答がここに表示されます。
          </p>
        )}
      </div>
    </section>
  );
}

/**
 * 要件検索とAI回答をタブで切り替える画面を表示する。
 *
 * 入力した質問とLevelはタブ間で共有し、検索結果とAI回答は個別に保持する。
 *
 * @returns {import("react").ReactElement} ASVS検索・AI回答ワークスペース。
 */
export default function SearchWorkspace() {
  const [activeTab, setActiveTab] = useState("search");
  const [query, setQuery] = useState("");
  const [level, setLevel] = useState(2);
  const [searchOperation, setSearchOperation] = useState(IDLE_OPERATION);
  const [answerOperation, setAnswerOperation] = useState(IDLE_OPERATION);
  const searchTabRef = useRef(null);
  const answerTabRef = useRef(null);
  const guidedTabRef = useRef(null);
  const queryInputRef = useRef(null);

  const activeOperation =
    activeTab === "search" ? searchOperation : answerOperation;

  /** 検索タブを選択する。引数と戻り値はない。 */
  function selectSearchTab() {
    setActiveTab("search");
  }

  /** AI回答タブを選択する。引数と戻り値はない。 */
  function selectAnswerTab() {
    setActiveTab("answer");
  }

  /** ガイド付きセキュリティレビュータブを選択する。引数と戻り値はない。 */
  function selectGuidedTab() {
    setActiveTab("guided");
  }

  /**
   * タブ上のキー操作を処理し、左右矢印・Home・Endで選択とフォーカスを移動する。
   *
   * @param {import("react").KeyboardEvent<HTMLButtonElement>} event - タブボタンのキーボードイベント。
   * @returns {void}
   */
  function handleTabKeyDown(event) {
    let nextTab;
    const tabs = ["search", "answer", "guided"];
    if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
      const offset = event.key === "ArrowRight" ? 1 : -1;
      nextTab = tabs[(tabs.indexOf(activeTab) + offset + tabs.length) % tabs.length];
    } else if (event.key === "Home") {
      nextTab = "search";
    } else if (event.key === "End") {
      nextTab = "guided";
    } else {
      return;
    }

    event.preventDefault();
    setActiveTab(nextTab);
    const nextTabRef = nextTab === "search" ? searchTabRef : nextTab === "answer" ? answerTabRef : guidedTabRef;
    nextTabRef.current?.focus();
  }

  /**
   * 質問入力の変更を画面状態へ反映する。
   *
   * @param {import("react").ChangeEvent<HTMLTextAreaElement>} event - 質問欄の変更イベント。
   * @returns {void}
   */
  function handleQueryChange(event) {
    setQuery(event.target.value);
  }

  /**
   * 対象Levelの変更を画面状態へ反映する。
   *
   * @param {import("react").ChangeEvent<HTMLSelectElement>} event - Level選択欄の変更イベント。
   * @returns {void}
   */
  function handleLevelChange(event) {
    setLevel(Number(event.target.value));
  }

  /**
   * 質問例を入力欄へ設定してフォーカスする。
   *
   * @param {import("react").MouseEvent<HTMLButtonElement>} event - data-exampleを持つ質問例ボタンのクリックイベント。
   * @returns {void}
   */
  function handleExampleClick(event) {
    setQuery(event.currentTarget.dataset.example ?? "");
    queryInputRef.current?.focus();
  }

  /**
   * 選択中のタブに応じ、要件検索またはAI回答生成を実行する。
   *
   * @param {import("react").FormEvent<HTMLFormElement>} event - 質問フォームの送信イベント。
   * @returns {Promise<void>} 通信と画面状態の更新完了を表すPromise。
   */
  async function handleSubmit(event) {
    event.preventDefault();
    const isAnswer = activeTab === "answer";
    const updateOperation = isAnswer
      ? setAnswerOperation
      : setSearchOperation;
    updateOperation({ phase: "loading", payload: null, error: "" });

    try {
      const payload = isAnswer
        ? await generateRequirementAnswer({ query, level })
        : await searchRequirements({ query, level });
      updateOperation({ phase: "success", payload, error: "" });
    } catch (error) {
      const fallbackMessage = isAnswer
        ? "AI回答の生成に失敗しました。"
        : "検索に失敗しました。";
      updateOperation({
        phase: "error",
        payload: null,
        error: error instanceof Error ? error.message : fallbackMessage,
      });
    }
  }

  return (
    <>
      <header className="site-header">
        <Link className="brand" href="/" aria-label="ASVS Requirement Finder ホーム">
          <span className="brand-mark" aria-hidden="true">
            A
          </span>
          <span>ASVS Requirement Finder</span>
        </Link>
        <nav className="site-nav" aria-label="サイト内ナビゲーション">
          <Link href="/how-to-use">使い方</Link>
          <Link href="/evaluation">RAG評価</Link>
          <span className="version-badge">ASVS 5.0.0</span>
        </nav>
      </header>

      <main>
        <div className="workspace-tabs" role="tablist" aria-label="利用方法">
          <button
            id="search-tab"
            ref={searchTabRef}
            type="button"
            role="tab"
            aria-selected={activeTab === "search"}
            aria-controls="search-panel"
            tabIndex={activeTab === "search" ? 0 : -1}
            onClick={selectSearchTab}
            onKeyDown={handleTabKeyDown}
          >
            要件検索
          </button>
          <button
            id="answer-tab"
            ref={answerTabRef}
            type="button"
            role="tab"
            aria-selected={activeTab === "answer"}
            aria-controls="answer-panel"
            tabIndex={activeTab === "answer" ? 0 : -1}
            onClick={selectAnswerTab}
            onKeyDown={handleTabKeyDown}
          >
            AI回答
          </button>
          <button id="guided-tab" ref={guidedTabRef} type="button" role="tab" aria-selected={activeTab === "guided"} aria-controls="guided-panel" tabIndex={activeTab === "guided" ? 0 : -1} onClick={selectGuidedTab} onKeyDown={handleTabKeyDown}>
            ガイド付きセキュリティレビュー
          </button>
        </div>

        <div
          id={activeTab === "search" ? "search-panel" : activeTab === "answer" ? "answer-panel" : "guided-panel"}
          role="tabpanel"
          aria-labelledby={activeTab === "search" ? "search-tab" : activeTab === "answer" ? "answer-tab" : "guided-tab"}
        >
          {activeTab === "guided" ? <GuidedRequirementsWorkspace /> : <>
          <section className="hero" aria-labelledby="page-title">
            <p className="eyebrow">
              APPLICATION SECURITY VERIFICATION STANDARD
            </p>
            <h1 id="page-title">
              {activeTab === "search" ? (
                <>
                  セキュリティ要件を、<br />日本語ですばやく探す。
                </>
              ) : (
                <>
                  ASVSを根拠に、<br />AIへ質問する。
                </>
              )}
            </h1>
            <p className="lead">
              {activeTab === "search"
                ? "Webアプリの設計・実装で気になることを入力すると、関連するOWASP ASVS要件を日本語訳と英語原文で提示します。"
                : "質問に関連するOWASP ASVS要件を検索し、その要件だけを根拠にAIが回答します。"}
            </p>

            <form className="search-panel" onSubmit={handleSubmit}>
              <label htmlFor="query">確認したいこと</label>
              <div className="search-row">
                <textarea
                  ref={queryInputRef}
                  id="query"
                  name="query"
                  rows="2"
                  minLength="2"
                  maxLength="200"
                  required
                  placeholder="例：パスワードを安全に保存するには？"
                  value={query}
                  onChange={handleQueryChange}
                />
                <button
                  id="submit-button"
                  type="submit"
                  disabled={activeOperation.phase === "loading"}
                >
                  {activeTab === "search" ? "要件を検索" : "AI回答を生成"}
                </button>
              </div>
              <div className="search-options">
                <label htmlFor="level">対象レベル</label>
                <select
                  id="level"
                  name="level"
                  value={level}
                  onChange={handleLevelChange}
                >
                  <option value="1">Level 1 — 基本</option>
                  <option value="2">Level 2 — 標準</option>
                  <option value="3">Level 3 — 高保証</option>
                </select>
                <span>選択したLevelまでを、Levelごとに最大5件抽出します</span>
              </div>
            </form>

            <aside className="level-guide" aria-label="ASVS LevelとRAG抽出の凡例">
              <h2>ASVS LevelとRAG抽出</h2>
              <dl>
                <div>
                  <dt>Level 1</dt>
                  <dd>一般的なWebアプリの基本的なセキュリティ要件。RAGはL1から最大5件を抽出します。</dd>
                </div>
                <div>
                  <dt>Level 2</dt>
                  <dd>個人情報や業務データを扱う多くのシステム向けの標準水準。L1とL2を別々に検索し、最大10件を抽出します。</dd>
                </div>
                <div>
                  <dt>Level 3</dt>
                  <dd>高い機密性や影響度を持つシステム向けの高保証水準。L1〜L3を別々に検索し、最大15件を抽出します。</dd>
                </div>
              </dl>
              <p>
                各Levelは完全一致で検索するため、下位Levelの結果によって上位Levelの根拠が表示されなくなることを防ぎます。AI回答では、抽出された全要件を根拠として使用します。
              </p>
            </aside>

            <div className="examples" aria-label="質問例">
              <span>質問例</span>
              <button
                type="button"
                data-example="パスワードの安全な保存"
                onClick={handleExampleClick}
              >
                パスワード保存
              </button>
              <button
                type="button"
                data-example="APIの認証と認可"
                onClick={handleExampleClick}
              >
                APIの認証・認可
              </button>
              <button
                type="button"
                data-example="ファイルアップロードの検証"
                onClick={handleExampleClick}
              >
                ファイル検証
              </button>
            </div>

          </section>

          {activeTab === "search" ? (
            <SearchResults operation={searchOperation} />
          ) : (
            <AnswerResults operation={answerOperation} />
          )}
          </>}
        </div>
      </main>

      <footer>
        <p>OWASP ASVS 5.0.0 / CC BY-SA 4.0</p>
        <p>OWASPによる公式な承認を示すものではありません。</p>
      </footer>
    </>
  );
}
