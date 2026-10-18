import Link from "next/link";

/** アプリの機能範囲と利用手順を説明するページを返す。 */
export default function HowToUsePage() {
  return <main className="how-to-use"><Link href="/">← ASVS Requirement Finderへ戻る</Link><p className="eyebrow">HOW TO USE</p><h1>ASVSを、機能要件のセキュリティ確認に使う。</h1><p className="lead">このアプリはASVS要件の探索と、機能要件に対するセキュリティレビューを支援します。適合性の自動判定や脆弱性診断を行うものではありません。</p><section><h2>3つの使い方</h2><ol><li><strong>要件検索</strong><br />技術や機能に関する質問から、関連するASVS要件を探します。</li><li><strong>AI回答</strong><br />取得済みのASVS要件だけを根拠に、質問への回答を確認します。</li><li><strong>ガイド付きセキュリティレビュー</strong><br />具体化済みの機能要件を入力すると、セキュリティ判断に必要な情報だけを確認し、追加すべき要件とASVS根拠を整理します。</li></ol></section><section><h2>入力する機能要件</h2><p>誰が、何を、どの条件で利用できるかを記載します。例: 「未ログイン利用者は口コミを3件まで閲覧でき、会員は全件を閲覧できる。投稿者だけが自分の口コミを編集・削除できる」。曖昧なアイデアから機能要件を作成する用途は対象外です。</p></section><section><h2>Levelの選び方</h2><p>L1は基本的なWebアプリ、L2は多くの業務・個人情報を扱うシステム、L3は高い機密性や影響度を持つシステムを想定します。選択したLevelまでを各Level最大5件ずつ抽出します。</p></section><section><h2>結果の読み方</h2><p>表示する要件IDと本文はASVSの根拠です。AIの提案、未確認事項、実装可否は区別して確認してください。最終的な設計判断とセキュリティレビューは担当者が行います。</p></section></main>;
}
