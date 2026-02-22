import { Router, Request, Response } from "express";

export function githubRoutes(
  record: (server: string, req: Request) => void
): Router {
  const router = Router();

  router.post("/graphql", (req: Request, res: Response) => {
    record("github", req);
    const query: string = req.body?.query || "";

    if (query.includes("reviewThreads")) {
      res.json({
        data: {
          repository: {
            pullRequest: {
              reviewThreads: { nodes: [] },
            },
          },
        },
      });
      return;
    }

    if (query.includes("resolveReviewThread")) {
      res.json({
        data: {
          resolveReviewThread: {
            thread: { isResolved: true },
          },
        },
      });
      return;
    }

    console.log(`[github] Unknown GraphQL: ${query.substring(0, 100)}`);
    res.json({ data: {} });
  });

  router.get(
    "/repos/:owner/:repo/issues/:number/comments",
    (req: Request, res: Response) => {
      record("github", req);
      res.json([]);
    }
  );

  router.post(
    "/repos/:owner/:repo/issues/:number/comments",
    (req: Request, res: Response) => {
      record("github", req);
      res.status(201).json({
        id: 1,
        body: req.body?.body || "",
        created_at: new Date().toISOString(),
      });
    }
  );

  router.post(
    "/repos/:owner/:repo/pulls/:number/reviews",
    (req: Request, res: Response) => {
      record("github", req);
      res.json({ id: 1, state: "COMMENTED", body: "" });
    }
  );

  router.post(
    "/repos/:owner/:repo/pulls/:number/comments",
    (req: Request, res: Response) => {
      record("github", req);
      res.status(201).json({
        id: 1,
        body: req.body?.body || "",
        created_at: new Date().toISOString(),
      });
    }
  );

  return router;
}

export function githubCatchAll(record: (server: string, req: Request) => void) {
  return (req: Request, res: Response) => {
    record("github", req);
    console.log(`[github] Unhandled: ${req.method} ${req.originalUrl}`);
    res.json({});
  };
}
