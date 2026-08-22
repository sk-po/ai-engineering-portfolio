import { cp, mkdir, rm } from "node:fs/promises";

const outputDirectory = new URL("../dist/", import.meta.url);

await rm(outputDirectory, { force: true, recursive: true });
await mkdir(outputDirectory, { recursive: true });
await cp(new URL("../index.html", import.meta.url), new URL("index.html", outputDirectory));
await cp(new URL("../src/", import.meta.url), new URL("src/", outputDirectory), {
  recursive: true,
});

console.log("Frontend build completed: dist/");
