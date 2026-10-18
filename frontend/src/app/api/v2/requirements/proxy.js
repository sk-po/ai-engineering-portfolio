const MAX_REQUEST_BODY_BYTES = 64 * 1024;
const BACKEND_TIMEOUT_MILLISECONDS = 60_000;

/**
 * ブラウザから受け取ったv2要件APIのPOSTをFastAPIへ転送する。
 *
 * @param {Request} request - Next.js Route Handlerが受信したWeb Request。
 * @param {string} backendPath - `/api/v2/requirements/`配下の転送先絶対パス。
 * @returns {Promise<Response>} バックエンドの本文とstatusを維持したResponse。設定不備は503、本文超過は413、通信失敗は502。
 */
export async function proxyRequirementPost(request, backendPath) {
  const backendUrl = process.env.BACKEND_URL;
  if (!backendUrl) {
    return Response.json(
      { detail: "BACKEND_URL is not configured" },
      { status: 503 },
    );
  }

  const reader = request.body?.getReader();
  const chunks = [];
  let size = 0;

  try {
    if (reader) {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        size += value.byteLength;
        if (size > MAX_REQUEST_BODY_BYTES) {
          await reader.cancel();
          return Response.json({ detail: "Request body is too large" }, { status: 413 });
        }
        chunks.push(Buffer.from(value));
      }
    }
    const upstream = await fetch(new URL(backendPath, backendUrl), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: Buffer.concat(chunks),
      cache: "no-store",
      signal: AbortSignal.timeout(BACKEND_TIMEOUT_MILLISECONDS),
    });
    const headers = {
      "Content-Type": upstream.headers.get("content-type") ?? "application/json",
      "Cache-Control": "no-store",
    };
    const requestId = upstream.headers.get("x-request-id");
    if (requestId) headers["X-Request-ID"] = requestId;
    return new Response(await upstream.arrayBuffer(), { status: upstream.status, headers });
  } catch {
    return Response.json({ detail: "Backend request failed" }, { status: 502 });
  } finally {
    reader?.releaseLock();
  }
}
