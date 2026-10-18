import Link from "next/link";
import React from "react";

import EvaluationOffline from "../../components/evaluation-offline.jsx";

export const metadata = {
  title: "RAG評価（オフライン） | ASVS Requirement Finder",
  description:
    "自作のゴールデンセットでRAGの検索・生成品質を実測し、run間で比較する記録。指標の意味と限界も明示します。",
};

/**
 * オフラインRAG評価ページを、共通ヘッダー・評価内ナビ・フッターとともに表示する。
 *
 * @returns {import("react").ReactElement} オフライン評価ページ。
 */
export default function EvaluationPage() {
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
            <Link href="/evaluation" aria-current="page">
              オフライン評価
            </Link>
            <Link href="/evaluation/online">オンライン評価</Link>
          </span>
        </nav>
        <EvaluationOffline />
      </main>

      <footer>
        <p>OWASP ASVS 5.0.0 / CC BY-SA 4.0</p>
        <p>評価値は自作ケースによる実測の単一runです。合否判定ではありません。</p>
      </footer>
    </>
  );
}
