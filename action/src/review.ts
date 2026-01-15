import * as exec from "@actions/exec";
import * as fs from "fs";
import * as path from "path";
import { getVersion } from "./config";
import { ReviewIssue, ReviewOutput } from "./types";

const OUTPUT_FILE = ".reviewcerberus-output.json";

export interface ReviewConfig {
  workspace: string;
  targetBranch: string;
  verify: boolean;
  instructions?: string;
  env: Record<string, string>;
}

export function filterByConfidence(
  issues: ReviewIssue[],
  minConfidence?: number
): ReviewIssue[] {
  if (minConfidence === undefined) {
    return issues;
  }

  return issues.filter((issue) => {
    // If issue has no confidence (verification not run), include it
    if (issue.confidence === undefined || issue.confidence === null) {
      return true;
    }
    return issue.confidence >= minConfidence;
  });
}

export async function runReview(config: ReviewConfig): Promise<ReviewOutput> {
  const version = getVersion();
  const outputPath = path.join(config.workspace, OUTPUT_FILE);

  // Build Docker args
  const dockerArgs = [
    "run",
    "--rm",
    // Run as current user to fix permission issues with mounted volumes
    "--user",
    `${process.getuid?.() ?? 1000}:${process.getgid?.() ?? 1000}`,
    "-v",
    `${config.workspace}:/repo`,
    // Fix git safe directory issue with mounted volumes
    "-e",
    "GIT_CONFIG_COUNT=1",
    "-e",
    "GIT_CONFIG_KEY_0=safe.directory",
    "-e",
    "GIT_CONFIG_VALUE_0=/repo",
  ];

  // Add environment variables from config
  for (const [key, value] of Object.entries(config.env)) {
    dockerArgs.push("-e", `${key}=${value}`);
  }

  // Add image
  dockerArgs.push(`kirill89/reviewcerberus-cli:${version}`);

  // Add CLI arguments
  dockerArgs.push("--json");
  dockerArgs.push("--output", `/repo/${OUTPUT_FILE}`);
  dockerArgs.push("--target-branch", config.targetBranch);

  if (config.verify) {
    dockerArgs.push("--verify");
  }

  if (config.instructions) {
    dockerArgs.push("--instructions", config.instructions);
  }

  // Execute Docker
  await exec.exec("docker", dockerArgs);

  // Read and parse output
  const outputContent = fs.readFileSync(outputPath, "utf-8");
  const review: ReviewOutput = JSON.parse(outputContent);

  // Clean up output file
  fs.unlinkSync(outputPath);

  return review;
}

export function parseReviewOutput(jsonString: string): ReviewOutput {
  return JSON.parse(jsonString) as ReviewOutput;
}
