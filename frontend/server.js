import { readFile } from "node:fs/promises";
import { createServer } from "node:http";
import { pathToFileURL } from "node:url";

const host = process.env.HOST ?? "127.0.0.1";
const port = Number.parseInt(process.env.PORT ?? "3000", 10);
const backendUrl = process.env.BACKEND_URL;
const maximumRequestBodyBytes = 64 * 1024;

const securityHeaders = {
  "Content-Security-Policy":
    "default-src 'self'; connect-src 'self'; img-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
  "Referrer-Policy": "no-referrer",
  "X-Content-Type-Options": "nosniff",
};

const publicFiles = new Map([
  ["/", ["index.html", "text/html; charset=utf-8"]],
  ["/src/main.js", ["src/main.js", "text/javascript; charset=utf-8"]],
  ["/src/asvs.js", ["src/asvs.js", "text/javascript; charset=utf-8"]],
  ["/src/greeting.js", ["src/greeting.js", "text/javascript; charset=utf-8"]],
  ["/src/style.css", ["src/style.css", "text/css; charset=utf-8"]],
]);

export function createAppServer() {
  return createServer(async (request, response) => {
    const pathname = new URL(request.url ?? "/", `http://${host}`).pathname;

    if (pathname.startsWith("/api/")) {
      await proxyApiRequest(request, response);
      return;
    }

    const file = publicFiles.get(pathname);

    if (!file) {
      response.writeHead(404, {
        ...securityHeaders,
        "Content-Type": "text/plain; charset=utf-8",
      });
      response.end("Not Found");
      return;
    }

    try {
      const body = await readFile(new URL(file[0], import.meta.url));
      response.writeHead(200, { ...securityHeaders, "Content-Type": file[1] });
      response.end(body);
    } catch (error) {
      console.error(error);
      response.writeHead(500, {
        ...securityHeaders,
        "Content-Type": "text/plain; charset=utf-8",
      });
      response.end("Internal Server Error");
    }
  });
}

async function proxyApiRequest(request, response) {
  if (!backendUrl) {
    response.writeHead(503, {
      ...securityHeaders,
      "Content-Type": "application/json; charset=utf-8",
    });
    response.end(JSON.stringify({ detail: "BACKEND_URL is not configured" }));
    return;
  }

  try {
    const chunks = [];
    let receivedBytes = 0;
    for await (const chunk of request) {
      receivedBytes += chunk.length;
      if (receivedBytes > maximumRequestBodyBytes) {
        response.writeHead(413, {
          ...securityHeaders,
          "Content-Type": "application/json; charset=utf-8",
        });
        response.end(JSON.stringify({ detail: "Request body is too large" }));
        return;
      }
      chunks.push(chunk);
    }
    const body = chunks.length > 0 ? Buffer.concat(chunks) : undefined;
    const upstream = await fetch(new URL(request.url ?? "/", backendUrl), {
      method: request.method,
      headers: {
        "content-type": request.headers["content-type"] ?? "application/json",
      },
      body,
    });
    const responseBody = Buffer.from(await upstream.arrayBuffer());
    response.writeHead(upstream.status, {
      ...securityHeaders,
      "Content-Type": upstream.headers.get("content-type") ?? "application/json",
    });
    response.end(responseBody);
  } catch (error) {
    console.error(error);
    response.writeHead(502, {
      ...securityHeaders,
      "Content-Type": "application/json; charset=utf-8",
    });
    response.end(JSON.stringify({ detail: "Backend request failed" }));
  }
}

const isEntryPoint =
  process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;

if (isEntryPoint) {
  createAppServer().listen(port, host, () => {
    console.log(`Frontend is running at http://${host}:${port}`);
  });
}
