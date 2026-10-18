import { proxyRequirementPost } from "../../requirements/proxy.js";

export const runtime = "nodejs";

/**
 * ガイド付き要件探索のターンPOSTをFastAPIへ転送する。
 *
 * @param {Request} request - Next.js Route Handlerが受信したWeb Request。
 * @returns {Promise<Response>} バックエンドの本文とstatusを維持したResponse。
 */
export async function POST(request) {
  return proxyRequirementPost(request, "/api/v2/guided-requirements/turn");
}
