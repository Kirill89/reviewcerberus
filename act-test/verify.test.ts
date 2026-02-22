import { describe, it, expect, beforeAll } from "vitest";
import * as fs from "fs";
import * as path from "path";

interface RecordedRequest {
  server: string;
  method: string;
  url: string;
  body: unknown;
  timestamp: number;
}

const REQUESTS_FILE = path.join(__dirname, ".mock-requests.json");

let requests: RecordedRequest[];

beforeAll(() => {
  if (!fs.existsSync(REQUESTS_FILE)) {
    throw new Error(
      `${REQUESTS_FILE} not found. Run 'npm test' (which runs run.ts first) to generate it.`
    );
  }
  requests = JSON.parse(fs.readFileSync(REQUESTS_FILE, "utf-8"));
});

function ollamaRequests() {
  return requests.filter((r) => r.server === "ollama");
}

function githubRequests() {
  return requests.filter((r) => r.server === "github");
}

describe("Ollama mock was called correctly", () => {
  it("received a POST /api/chat request", () => {
    const chatRequests = ollamaRequests().filter(
      (r) => r.method === "POST" && r.url === "/api/chat"
    );
    expect(chatRequests.length).toBeGreaterThanOrEqual(1);
  });
});

describe("GitHub API mock was called correctly", () => {
  it("received a GraphQL reviewThreads query", () => {
    const graphqlRequests = githubRequests().filter(
      (r) =>
        r.method === "POST" &&
        r.url === "/graphql" &&
        typeof r.body === "object" &&
        r.body !== null &&
        "query" in r.body &&
        typeof (r.body as { query: string }).query === "string" &&
        (r.body as { query: string }).query.includes("reviewThreads")
    );
    expect(graphqlRequests.length).toBeGreaterThanOrEqual(1);
  });

  it("received a POST to create summary comment", () => {
    const commentRequests = githubRequests().filter(
      (r) =>
        r.method === "POST" &&
        /\/repos\/[^/]+\/[^/]+\/issues\/\d+\/comments/.test(r.url)
    );
    expect(commentRequests.length).toBeGreaterThanOrEqual(1);
  });

  it("received a POST to create review", () => {
    const reviewRequests = githubRequests().filter(
      (r) =>
        r.method === "POST" &&
        /\/repos\/[^/]+\/[^/]+\/pulls\/\d+\/reviews/.test(r.url)
    );
    expect(reviewRequests.length).toBeGreaterThanOrEqual(1);
  });
});
