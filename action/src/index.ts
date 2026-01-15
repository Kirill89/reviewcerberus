import * as core from "@actions/core";
import * as exec from "@actions/exec";
import * as github from "@actions/github";
import { getActionInputs, getDockerEnv } from "./config";
import {
  createOrUpdateSummary,
  createReview,
  getGitHubContext,
  resolveOurThreads,
} from "./github";
import {
  renderLineComment,
  renderSummaryComment,
  sortIssuesBySeverity,
} from "./render";
import { filterByConfidence, runReview, ReviewConfig } from "./review";
import { ReviewComment } from "./types";

async function run(): Promise<void> {
  try {
    // Get inputs
    const inputs = getActionInputs();
    const dockerEnv = getDockerEnv();

    // Get GitHub context
    const ctx = getGitHubContext();
    const octokit = github.getOctokit(inputs.githubToken);

    // Get target branch from PR
    const targetBranch =
      github.context.payload.pull_request?.base?.ref || "main";
    const workspace = process.env.GITHUB_WORKSPACE!;

    core.info(`Running ReviewCerberus on PR #${ctx.pullNumber}`);
    core.info(`Target branch: ${targetBranch}`);
    core.info(`Model provider: ${dockerEnv.MODEL_PROVIDER}`);

    // Fetch target branch to ensure it's available locally
    core.info(`Fetching target branch: ${targetBranch}`);
    await exec.exec("git", [
      "fetch",
      "origin",
      `${targetBranch}:${targetBranch}`,
    ]);

    // Build review config
    const config: ReviewConfig = {
      workspace,
      targetBranch,
      verify: inputs.verify,
      instructions: inputs.instructions,
      env: dockerEnv,
    };

    // Run the review
    core.info("Running code review...");
    const reviewOutput = await runReview(config);

    // Filter issues by confidence if specified
    let issues = reviewOutput.issues;
    if (inputs.minConfidence !== undefined) {
      const originalCount = issues.length;
      issues = filterByConfidence(issues, inputs.minConfidence);
      core.info(
        `Filtered ${originalCount - issues.length} issues below confidence ${inputs.minConfidence}`
      );
    }

    // Update the output with filtered issues
    const filteredOutput = {
      ...reviewOutput,
      issues,
    };

    // Resolve old review threads
    core.info("Resolving old review threads...");
    const resolvedCount = await resolveOurThreads(octokit, ctx);
    if (resolvedCount > 0) {
      core.info(`Resolved ${resolvedCount} old review threads`);
    }

    // Create or update summary comment
    core.info("Posting summary comment...");
    const summaryBody = renderSummaryComment(filteredOutput);
    await createOrUpdateSummary(octokit, ctx, summaryBody);

    // Create review with line comments
    const comments: ReviewComment[] = sortIssuesBySeverity(issues)
      .filter((issue) => issue.location[0])
      .map((issue) => {
        const loc = issue.location[0];
        return {
          path: loc.filename,
          body: renderLineComment(issue),
          ...(loc.line ? { line: loc.line } : {}),
        };
      });

    await createReview(octokit, ctx, comments);

    core.info(`Review completed: ${issues.length} issue(s) found`);
  } catch (error) {
    if (error instanceof Error) {
      core.setFailed(error.message);
    } else {
      core.setFailed("An unexpected error occurred");
    }
  }
}

run();
