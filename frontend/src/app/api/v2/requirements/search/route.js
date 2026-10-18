import { proxyRequirementPost } from "../proxy.js";

export const runtime = "nodejs";

/**
 * Level別RAG検索POSTをFastAPIへ転送する。
 *
 * @param {Request} request - Next.js Route Handlerが受信したWeb Request。
 * @returns {Promise<Response>} 検索APIの本文とstatusを維持したResponse。
 */
export async function POST(request) {
  return proxyRequirementPost(request, "/api/v2/requirements/search");
}
