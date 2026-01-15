import * as core from "@actions/core";
import * as github from "@actions/github";
import { ReviewComment } from "./types";
import { MARKER_ISSUE, MARKER_SUMMARY } from "./render";

type Octokit = ReturnType<typeof github.getOctokit>;

export interface GitHubContext {
  owner: string;
  repo: string;
  pullNumber: number;
  commitSha: string;
}

export function getGitHubContext(): GitHubContext {
  const context = github.context;

  if (!context.payload.pull_request) {
    throw new Error("This action can only be run on pull_request events");
  }

  return {
    owner: context.repo.owner,
    repo: context.repo.repo,
    pullNumber: context.payload.pull_request.number,
    commitSha: context.payload.pull_request.head.sha,
  };
}

export async function findSummaryComment(
  octokit: Octokit,
  ctx: GitHubContext
): Promise<number | null> {
  const { data: comments } = await octokit.rest.issues.listComments({
    owner: ctx.owner,
    repo: ctx.repo,
    issue_number: ctx.pullNumber,
  });

  for (const comment of comments) {
    if (comment.body?.includes(MARKER_SUMMARY)) {
      return comment.id;
    }
  }

  return null;
}

export async function createOrUpdateSummary(
  octokit: Octokit,
  ctx: GitHubContext,
  body: string
): Promise<void> {
  const existingCommentId = await findSummaryComment(octokit, ctx);

  if (existingCommentId) {
    core.info(`Updating existing summary comment (ID: ${existingCommentId})`);
    await octokit.rest.issues.updateComment({
      owner: ctx.owner,
      repo: ctx.repo,
      comment_id: existingCommentId,
      body,
    });
  } else {
    core.info("Creating new summary comment");
    await octokit.rest.issues.createComment({
      owner: ctx.owner,
      repo: ctx.repo,
      issue_number: ctx.pullNumber,
      body,
    });
  }
}

interface ReviewThread {
  id: string;
  isResolved: boolean;
  comments: {
    nodes: Array<{
      body: string;
    }>;
  };
}

interface PullRequestReviewThreads {
  repository: {
    pullRequest: {
      reviewThreads: {
        nodes: ReviewThread[];
      };
    };
  };
}

export async function getReviewThreads(
  octokit: Octokit,
  ctx: GitHubContext
): Promise<ReviewThread[]> {
  const query = `
    query($owner: String!, $repo: String!, $pullNumber: Int!) {
      repository(owner: $owner, name: $repo) {
        pullRequest(number: $pullNumber) {
          reviewThreads(first: 100) {
            nodes {
              id
              isResolved
              comments(first: 1) {
                nodes {
                  body
                }
              }
            }
          }
        }
      }
    }
  `;

  const result = await octokit.graphql<PullRequestReviewThreads>(query, {
    owner: ctx.owner,
    repo: ctx.repo,
    pullNumber: ctx.pullNumber,
  });

  return result.repository.pullRequest.reviewThreads.nodes;
}

export async function resolveThread(
  octokit: Octokit,
  threadId: string
): Promise<void> {
  const mutation = `
    mutation($threadId: ID!) {
      resolveReviewThread(input: { threadId: $threadId }) {
        thread {
          isResolved
        }
      }
    }
  `;

  await octokit.graphql(mutation, { threadId });
}

export async function resolveOurThreads(
  octokit: Octokit,
  ctx: GitHubContext
): Promise<number> {
  const threads = await getReviewThreads(octokit, ctx);
  let resolvedCount = 0;

  for (const thread of threads) {
    // Skip already resolved threads
    if (thread.isResolved) {
      continue;
    }

    // Check if this thread was created by us (has our marker)
    const firstComment = thread.comments.nodes[0];
    if (firstComment?.body?.includes(MARKER_ISSUE)) {
      core.info(`Resolving thread ${thread.id}`);
      await resolveThread(octokit, thread.id);
      resolvedCount++;
    }
  }

  return resolvedCount;
}

export async function createReview(
  octokit: Octokit,
  ctx: GitHubContext,
  comments: ReviewComment[]
): Promise<void> {
  if (comments.length === 0) {
    core.info("No comments to post");
    return;
  }

  core.info(`Creating review with ${comments.length} comments`);

  // Format comments for the API
  const formattedComments = comments.map((comment) => ({
    path: comment.path,
    body: comment.body,
    ...(comment.line ? { line: comment.line } : {}),
  }));

  try {
    await octokit.rest.pulls.createReview({
      owner: ctx.owner,
      repo: ctx.repo,
      pull_number: ctx.pullNumber,
      commit_id: ctx.commitSha,
      event: "COMMENT",
      comments: formattedComments,
    });
  } catch (error) {
    // If batch fails, try posting comments individually
    core.warning(
      `Batch review creation failed, trying individual comments: ${error}`
    );

    for (const comment of formattedComments) {
      try {
        await octokit.rest.pulls.createReviewComment({
          owner: ctx.owner,
          repo: ctx.repo,
          pull_number: ctx.pullNumber,
          commit_id: ctx.commitSha,
          body: comment.body,
          path: comment.path,
          ...(comment.line ? { line: comment.line } : {}),
        });
      } catch (commentError) {
        // If line comment fails, try as file-level comment
        if (comment.line) {
          core.info(
            `Line ${comment.line} not in diff, posting as file-level comment on ${comment.path}`
          );
          try {
            await octokit.rest.pulls.createReviewComment({
              owner: ctx.owner,
              repo: ctx.repo,
              pull_number: ctx.pullNumber,
              commit_id: ctx.commitSha,
              body: `**Line ${comment.line}:**\n\n${comment.body}`,
              path: comment.path,
              subject_type: "file",
            });
          } catch (fileCommentError) {
            core.warning(
              `Failed to post file comment on ${comment.path}: ${fileCommentError}`
            );
          }
        } else {
          core.warning(
            `Failed to post comment on ${comment.path}: ${commentError}`
          );
        }
      }
    }
  }
}
