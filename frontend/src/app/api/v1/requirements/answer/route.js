import { proxyRequirementPost } from "../proxy.js";

export const runtime = "nodejs";

/**
 * AI回答POSTをFastAPIへ転送する。
 *
 * @param {Request} request - Next.js Route Handlerが受信したWeb Request。
 * @returns {Promise<Response>} AI回答APIの本文とstatusを維持したResponse。
 */
export async function POST(request) {
  return proxyRequirementPost(request, "/api/v1/requirements/answer");
}
