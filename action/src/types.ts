export type Severity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export type Category =
  | "LOGIC"
  | "SECURITY"
  | "ACCESS_CONTROL"
  | "PERFORMANCE"
  | "QUALITY"
  | "SIDE_EFFECTS"
  | "TESTING"
  | "DOCUMENTATION";

export interface IssueLocation {
  filename: string;
  line?: number | null;
}

export interface ReviewIssue {
  title: string;
  category: Category;
  severity: Severity;
  location: IssueLocation[];
  explanation: string;
  suggested_fix: string;
  confidence?: number | null;
  rationale?: string | null;
}

export interface ReviewOutput {
  description: string;
  issues: ReviewIssue[];
}

export interface ReviewComment {
  path: string;
  body: string;
  line?: number;
}
