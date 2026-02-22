import { Router, Request, Response } from "express";
import * as fs from "fs";
import * as path from "path";

const REVIEW_OUTPUT = JSON.parse(
  fs.readFileSync(
    path.join(__dirname, "fixtures", "review-output.json"),
    "utf-8"
  )
);

export function ollamaRoutes(
  record: (server: string, req: Request) => void
): Router {
  const router = Router();

  router.post("/api/chat", (req: Request, res: Response) => {
    record("ollama", req);

    const tools: Array<{ function?: { name?: string } }> =
      req.body?.tools || [];
    const streaming = req.body?.stream === true;

    // Find the response format tool (PrimaryReviewOutput) if tools are present
    const responseToolName =
      tools.find((t) => t.function?.name === "PrimaryReviewOutput")?.function
        ?.name || null;

    // Build the response message: tool call if tools present, plain content otherwise
    const message = responseToolName
      ? {
          role: "assistant",
          content: "",
          tool_calls: [
            {
              function: {
                name: responseToolName,
                arguments: REVIEW_OUTPUT,
              },
            },
          ],
        }
      : {
          role: "assistant",
          content: JSON.stringify(REVIEW_OUTPUT),
        };

    const response = {
      model: req.body?.model || "mock-model",
      created_at: new Date().toISOString(),
      message,
      done: true,
      done_reason: "stop",
      total_duration: 1000000,
      load_duration: 100000,
      prompt_eval_count: 100,
      prompt_eval_duration: 500000,
      eval_count: 50,
      eval_duration: 500000,
    };

    if (streaming) {
      res.setHeader("Content-Type", "application/x-ndjson");
      res.write(JSON.stringify(response) + "\n");
      res.end();
    } else {
      res.json(response);
    }
  });

  return router;
}

export function ollamaCatchAll(record: (server: string, req: Request) => void) {
  return (req: Request, res: Response) => {
    record("ollama", req);
    res.status(404).json({ error: "not found" });
  };
}
