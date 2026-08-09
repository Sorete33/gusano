import { readFileSync, writeFileSync } from "node:fs";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);
const CONCURRENCY = 5;
const FORCE = process.argv.includes("--force");

const yml = readFileSync("data/playlist.yml", "utf8");
const urls = [
  ...new Set(
    [...yml.matchAll(/^\s*url:\s*["']([^"']+)["']/gm)].map((m) => m[1])
  ),
];

let durations = {};
try {
  durations = JSON.parse(readFileSync("data/playlist-durations.json", "utf8"));
} catch (e) {
  durations = {};
}

const toProbe = urls.filter((u) => FORCE || durations[u] == null);

async function probe(url) {
  const target = url.startsWith("/") ? "static" + url : url;
  try {
    const { stdout } = await execFileAsync(
      "ffprobe",
      [
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "csv=p=0",
        target,
      ],
      { timeout: 60000 }
    );
    const seconds = Math.round(parseFloat(stdout.trim()));
    if (!Number.isNaN(seconds)) {
      durations[url] = seconds;
      console.log(url, "->", seconds + "s");
    } else {
      console.warn("Could not parse duration for", url);
    }
  } catch (e) {
    console.warn("Failed to probe", url, e.message);
  }
}

let index = 0;
async function worker() {
  while (index < toProbe.length) {
    const url = toProbe[index++];
    await probe(url);
  }
}

await Promise.all(
  Array.from(
    { length: Math.min(CONCURRENCY, toProbe.length) },
    () => worker()
  )
);

writeFileSync(
  "data/playlist-durations.json",
  JSON.stringify(durations, null, 2) + "\n"
);
console.log(
  "Wrote data/playlist-durations.json with",
  Object.keys(durations).length,
  "durations."
);
