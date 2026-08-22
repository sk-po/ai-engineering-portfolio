import { readFile } from "node:fs/promises";
import { createServer } from "node:http";
import { pathToFileURL } from "node:url";

const host = process.env.HOST ?? "127.0.0.1";
const port = Number.parseInt(process.env.PORT ?? "3000", 10);

const publicFiles = new Map([
  ["/", ["index.html", "text/html; charset=utf-8"]],
  ["/src/main.js", ["src/main.js", "text/javascript; charset=utf-8"]],
  ["/src/greeting.js", ["src/greeting.js", "text/javascript; charset=utf-8"]],
  ["/src/style.css", ["src/style.css", "text/css; charset=utf-8"]],
]);

export function createAppServer() {
  return createServer(async (request, response) => {
    const pathname = new URL(request.url ?? "/", `http://${host}`).pathname;
    const file = publicFiles.get(pathname);

    if (!file) {
      response.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
      response.end("Not Found");
      return;
    }

    try {
      const body = await readFile(new URL(file[0], import.meta.url));
      response.writeHead(200, { "Content-Type": file[1] });
      response.end(body);
    } catch (error) {
      console.error(error);
      response.writeHead(500, { "Content-Type": "text/plain; charset=utf-8" });
      response.end("Internal Server Error");
    }
  });
}

const isEntryPoint =
  process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;

if (isEntryPoint) {
  createAppServer().listen(port, host, () => {
    console.log(`Frontend is running at http://${host}:${port}`);
  });
}
