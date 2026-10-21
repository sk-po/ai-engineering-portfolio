"use client";

import React, { useState } from "react";

import { guideRequirements } from "../asvs.js";

/**
 * 選択Levelに応じたRAG抽出件数の説明文を返す。各Levelから最大5件を積み上げる。
 *
 * @param {number} level - 対象Level（1〜3）。
 * @returns {string} 抽出条件の説明文。Level1は5件、以降は合計を明示する。
 */
function levelRetrievalText(level) {
  if (level <= 1) return "Level 1：最大5件を抽出します";
  return `Level 1〜${level}：各Level最大5件（合計最大${level * 5}件）を抽出します`;
}

/** ガイド付きセキュリティレビューを表示し、質問と回答のターンを画面状態として保持する。 */
export default function GuidedRequirementsWorkspace() {
  const [featureDescription, setFeatureDescription] = useState("");
  const [answers, setAnswers] = useState([]);
  const [response, setResponse] = useState(null);
  const [currentAnswer, setCurrentAnswer] = useState("");
  const [level, setLevel] = useState(2);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  /** 現在の説明または回答を送信して、次のヒアリングターンを取得する。 */
  async function submit(event) {
    event.preventDefault();
    const nextAnswers = response?.action === "ask" ? [...answers, currentAnswer] : answers;
    setLoading(true);
    setError("");
    try {
      const payload = await guideRequirements({ featureDescription, answers: nextAnswers, level });
      setAnswers(nextAnswers);
      setCurrentAnswer("");
      setResponse(payload);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "セキュリティレビューを続行できませんでした。");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="guided-workspace" aria-labelledby="guided-title">
      <p className="eyebrow">APPLICATION SECURITY VERIFICATION STANDARD</p>
      <h1 id="guided-title">機能要件のセキュリティ観点を点検する</h1>
      <p className="lead">具体化済みの機能要件を入力してください。セキュリティ判断に必要な情報だけを質問し、ASVS根拠と追加すべき要件を整理します。</p>
      <form className="search-panel" onSubmit={submit}>
        <label htmlFor="guided-feature">レビュー対象の機能要件</label>
        <textarea id="guided-feature" required minLength="20" maxLength="1000" value={featureDescription} disabled={Boolean(response)} onChange={(event) => setFeatureDescription(event.target.value)} placeholder="例：未ログイン利用者は口コミを3件まで閲覧でき、会員は全件を閲覧できる。投稿者だけが自分の口コミを編集・削除できる。" />
        <div className="search-options">
          <label htmlFor="guided-level">対象レベル</label>
          <select id="guided-level" value={level} disabled={Boolean(response)} onChange={(event) => setLevel(Number(event.target.value))}>
            <option value="1">Level 1 — 基本</option><option value="2">Level 2 — 標準</option><option value="3">Level 3 — 高保証</option>
          </select>
          <span>{levelRetrievalText(level)}</span>
        </div>
        {response?.action === "ask" ? <><label htmlFor="guided-answer">質問 {response.turn}: {response.question}</label><textarea id="guided-answer" required minLength="2" maxLength="500" value={currentAnswer} onChange={(event) => setCurrentAnswer(event.target.value)} /></> : null}
        <button id="submit-button" type="submit" disabled={loading}>{loading ? "レビューしています…" : response?.action === "ask" ? "回答して続ける" : "レビューを開始する"}</button>
      </form>
      {error ? <p role="status" className="guided-error">{error}</p> : null}
      {response ? <section className="guided-result"><h2>{response.action === "ask" ? "セキュリティ上の確認事項" : "セキュリティ要件レビュー結果"}</h2><p>{response.missing_topics?.join("、") || "確認事項を整理しています。"}</p>{response.answer ? <p className="answer-text">{response.answer}</p> : null}{response.sources?.length ? <><h3>RAGの根拠</h3><ul>{response.sources.map((source) => <li key={source.requirement_id}>{source.requirement_id} — {source.description_ja}</li>)}</ul></> : null}</section> : null}
    </section>
  );
}
