import { fileURLToPath } from "node:url";

const config = {
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  turbopack: { root: fileURLToPath(new URL(".", import.meta.url)) },
  output: process.env.NEXT_STANDALONE === "1" ? "standalone" : undefined,
  poweredByHeader: false,
  /** 全ルートへ基本セキュリティヘッダーを返す。引数なし。Nextのscript実行を妨げる固定CSPは設定しない。 */
  async headers() {
    return [{ source: "/:path*", headers: [
      { key: "X-Content-Type-Options", value: "nosniff" },
      { key: "Referrer-Policy", value: "no-referrer" },
      { key: "X-Frame-Options", value: "DENY" },
    ] }];
  },
};
export default config;
