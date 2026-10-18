import Link from "next/link";
import React from "react";

import EvaluationOnline from "../../../components/evaluation-online.jsx";

export const metadata = {
  title: "RAG評価（オンライン） | ASVS Requirement Finder",
  description:
    "本番トラフィックを正解ラベル無しのシグナルで監視し、ゴールデンセットへ還流する設計。現時点では未計測の設計ビューです。",
};

/**
 * オンラインRAG評価ページを、共通ヘッダー・評価内ナビ・フッターとともに表示する。
 *
 * @returns {import("react").ReactElement} オンライン評価ページ。
 */
export default function EvaluationOnlinePage() {
  return (
    <>
      <header className="site-header">
        <Link className="brand" href="/" aria-label="ASVS Requirement Finder ホーム">
          <span className="brand-mark" aria-hidden="true">
            A
          </span>
          <span>ASVS Requirement Finder</span>
        </Link>
        <span className="version-badge">ASVS 5.0.0</span>
      </header>

      <main className="evaluation">
        <nav className="eval-subnav" aria-label="評価ビューの切り替え">
          <Link href="/">← アプリへ戻る</Link>
          <span className="eval-subnav-tabs">
            <Link href="/evaluation">オフライン評価</Link>
            <Link href="/evaluation/online" aria-current="page">
              オンライン評価
            </Link>
          </span>
        </nav>
        <EvaluationOnline />
      </main>

      <footer>
        <p>OWASP ASVS 5.0.0 / CC BY-SA 4.0</p>
        <p>オンライン評価は設計のみ。数値はデータストア整備後に表示します。</p>
      </footer>
    </>
  );
}
