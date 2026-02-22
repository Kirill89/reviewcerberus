import express, { Request } from "express";
import * as fs from "fs";
import * as path from "path";
import { Server } from "http";
import { ollamaRoutes, ollamaCatchAll } from "./ollama-routes";
import { githubRoutes, githubCatchAll } from "./github-routes";

export const OLLAMA_PORT = 42000;
export const GITHUB_PORT = 43000;
const REQUESTS_FILE = path.join(__dirname, ".mock-requests.json");

// --- Request recording ---

interface RecordedRequest {
  server: string;
  method: string;
  url: string;
  body: unknown;
  timestamp: number;
}

const recorded: RecordedRequest[] = [];

function record(server: string, req: Request): void {
  recorded.push({
    server,
    method: req.method,
    url: req.originalUrl,
    body: req.body,
    timestamp: Date.now(),
  });
  console.log(`[${server}] ${req.method} ${req.originalUrl}`);
  flushRecords();
}

function flushRecords(): void {
  fs.writeFileSync(REQUESTS_FILE, JSON.stringify(recorded, null, 2));
  console.log(
    `\nWrote ${recorded.length} recorded requests to ${REQUESTS_FILE}`
  );
}

// --- Express apps ---

const ollama = express();
ollama.use(express.json({ limit: "5mb" }));
ollama.use(ollamaRoutes(record));
ollama.use(ollamaCatchAll(record));

const github = express();
github.use(express.json({ limit: "5mb" }));
github.use(githubRoutes(record));
github.use(githubCatchAll(record));

// --- Public API ---

let ollamaServer: Server | null = null;
let githubServer: Server | null = null;

export function startMockServers(): Promise<void> {
  recorded.length = 0;
  if (fs.existsSync(REQUESTS_FILE)) fs.unlinkSync(REQUESTS_FILE);
  return new Promise((resolve) => {
    let started = 0;
    const onReady = () => {
      started++;
      if (started === 2) resolve();
    };
    ollamaServer = ollama.listen(OLLAMA_PORT, () => {
      console.log(`Mock Ollama listening on :${OLLAMA_PORT}`);
      onReady();
    });
    githubServer = github.listen(GITHUB_PORT, () => {
      console.log(`Mock GitHub API listening on :${GITHUB_PORT}`);
      onReady();
    });
  });
}

export function stopMockServers(): Promise<void> {
  return new Promise((resolve) => {
    let closed = 0;
    const onClosed = () => {
      closed++;
      if (closed === 2) resolve();
    };
    if (ollamaServer) ollamaServer.close(() => onClosed());
    else onClosed();
    if (githubServer) githubServer.close(() => onClosed());
    else onClosed();
  });
}
