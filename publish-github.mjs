import { promises as fs } from "node:fs";
import path from "node:path";
import { Script } from "node:vm";

const owner = "JeremyDays";
const repo = "iAccess-Rechenzentrum";
const token = process.env.GITHUB_TOKEN;
const api = "https://api.github.com";

if (!token) {
  console.error("GITHUB_TOKEN is required.");
  process.exit(1);
}

const headers = {
  Authorization: `Bearer ${token}`,
  Accept: "application/vnd.github+json",
  "X-GitHub-Api-Version": "2022-11-28",
  "User-Agent": "iaccess-rechenzentrum-publisher",
};

async function request(route, options = {}) {
  const response = await fetch(`${api}${route}`, {
    ...options,
    headers: { ...headers, ...(options.headers ?? {}) },
  });
  const text = await response.text();
  const body = text ? JSON.parse(text) : null;
  if (!response.ok) {
    const error = new Error(`${options.method ?? "GET"} ${route}: ${response.status} ${body?.message ?? response.statusText}`);
    error.status = response.status;
    error.body = body;
    throw error;
  }
  return body;
}

async function ensureRepo() {
  try {
    return await request(`/repos/${owner}/${repo}`);
  } catch (error) {
    if (error.status !== 404) throw error;
    return await request("/user/repos", {
      method: "POST",
      body: JSON.stringify({
        name: repo,
        description: "iAccess Datenraum Rechenzentren",
        private: false,
        auto_init: true,
      }),
    });
  }
}

async function getSha(remotePath, branch) {
  try {
    const current = await request(`/repos/${owner}/${repo}/contents/${encodeURIComponent(remotePath)}?ref=${branch}`);
    return current.sha;
  } catch (error) {
    if (error.status === 404) return undefined;
    throw error;
  }
}

async function upload(localPath, remotePath, branch) {
  const bytes = await fs.readFile(localPath);
  const sha = await getSha(remotePath, branch);
  const result = await request(`/repos/${owner}/${repo}/contents/${encodeURIComponent(remotePath)}`, {
    method: "PUT",
    body: JSON.stringify({
      message: `Publish ${remotePath}`,
      content: bytes.toString("base64"),
      branch,
      ...(sha ? { sha } : {}),
    }),
  });
  return result.commit.sha;
}

async function enablePages(branch) {
  try {
    await request(`/repos/${owner}/${repo}/pages`, {
      method: "POST",
      body: JSON.stringify({ source: { branch, path: "/" } }),
    });
    return "created";
  } catch (error) {
    if (error.status !== 409 && error.status !== 422) throw error;
    await request(`/repos/${owner}/${repo}/pages`, {
      method: "PUT",
      body: JSON.stringify({ source: { branch, path: "/" } }),
    });
    return "updated";
  }
}

async function validateIndexHtml() {
  const filename = "index.html";
  const html = await fs.readFile(filename, "utf8");
  const scripts = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)];

  if (scripts.length === 0) {
    throw new Error(`${filename}: no inline scripts found; refusing to publish an unvalidated app.`);
  }

  for (const [index, match] of scripts.entries()) {
    const source = match[1].trim();
    if (!source) continue;
    try {
      new Script(source, { filename: `${filename} inline script ${index + 1}` });
    } catch (error) {
      throw new Error(`${filename}: JavaScript syntax validation failed in inline script ${index + 1}: ${error.message}`);
    }
  }

  console.log(`${filename}: JavaScript syntax validation passed (${scripts.length} inline scripts).`);
}

await validateIndexHtml();

const repoInfo = await ensureRepo();
const branch = repoInfo.default_branch || "main";
const files = [
  ["index.html", "index.html"],
  ["database.json", "database.json"],
  [path.join("assets", "bw-municipality-coverage.json"), "assets/bw-municipality-coverage.json"],
  ["link-check-results.json", "link-check-results.json"],
  ["pdf-availability.json", "pdf-availability.json"],
  [path.join(".github", "ISSUE_TEMPLATE", "research-question.md"), ".github/ISSUE_TEMPLATE/research-question.md"],
  [path.join("pdfs", "manual-uploads", ".gitkeep"), "pdfs/manual-uploads/.gitkeep"],
  [path.join("assets", "iAccess-Logo-S.png"), "assets/iAccess-Logo-S.png"],
  [path.join("assets", "gis", "rechenzentren-deutschland.geojson"), "assets/gis/rechenzentren-deutschland.geojson"],
  [path.join("assets", "gis", "rechenzentren-deutschland.csv"), "assets/gis/rechenzentren-deutschland.csv"],
  [path.join("assets", "gis", "iaccess-rechenzentren-deutschland.qgs"), "assets/gis/iaccess-rechenzentren-deutschland.qgs"],
  [path.join("docs", "Internet-Glasfaser-Carrier-Grundlagen-fuer-Rechenzentren.pdf"), "docs/Internet-Glasfaser-Carrier-Grundlagen-fuer-Rechenzentren.pdf"],
];

for (const entry of await fs.readdir("docs")) {
  if (/^recherchefragen-\d{4}-\d{2}-\d{2}\.pdf$/i.test(entry)) {
    files.push([path.join("docs", entry), `docs/${entry}`]);
  }
  if (/^tagesbericht-\d{4}-\d{2}-\d{2}\.txt$/i.test(entry) || /^daily-report-\d{4}-\d{2}-\d{2}\.txt$/i.test(entry)) {
    files.push([path.join("docs", entry), `docs/${entry}`]);
  }
}

for (const entry of await fs.readdir("pdfs")) {
  if (/\.pdf$/i.test(entry)) {
    files.push([path.join("pdfs", entry), `pdfs/${entry}`]);
  }
}

for (const [localPath, remotePath] of files) {
  const sha = await upload(localPath, remotePath, branch);
  console.log(`${remotePath} ${sha}`);
}

const pagesStatus = await enablePages(branch);
const pages = await request(`/repos/${owner}/${repo}/pages`);

console.log(`pages ${pagesStatus} ${pages.html_url}`);
