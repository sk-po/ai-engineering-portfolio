import "../style.css";

export const metadata = {
  title: "ASVS Requirement Finder",
  description: "OWASP ASVS 5.0.0のセキュリティ要件を日本語で検索",
};

/** 全ページ共通の日本語HTMLを返す。childrenはページ内容。 */
export default function RootLayout({ children }) {
  return <html lang="ja"><body>{children}</body></html>;
}
