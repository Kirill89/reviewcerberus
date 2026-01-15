import { describe, it, expect } from "vitest";
import {
  renderLineComment,
  renderSummaryComment,
  sortIssuesBySeverity,
  MARKER_SUMMARY,
  MARKER_ISSUE,
} from "../src/render";
import { ReviewIssue, ReviewOutput } from "../src/types";

describe("renderLineComment", () => {
  it("includes marker", () => {
    const issue: ReviewIssue = {
      title: "Null check missing",
      severity: "HIGH",
      category: "LOGIC",
      location: [{ filename: "src/main.py", line: 42 }],
      explanation: "The variable could be null",
      suggested_fix: "Add a null check",
    };
    const result = renderLineComment(issue);
    expect(result).toContain(MARKER_ISSUE);
  });

  it("includes severity emoji for CRITICAL", () => {
    const issue: ReviewIssue = {
      title: "SQL Injection",
      severity: "CRITICAL",
      category: "SECURITY",
      location: [{ filename: "src/db.py" }],
      explanation: "User input is not sanitized",
      suggested_fix: "Use parameterized queries",
    };
    const result = renderLineComment(issue);
    expect(result).toContain("\u{1F534}"); // Red circle emoji
    expect(result).toContain("CRITICAL");
  });

  it("includes severity emoji for HIGH", () => {
    const issue: ReviewIssue = {
      title: "Race condition",
      severity: "HIGH",
      category: "LOGIC",
      location: [{ filename: "src/thread.py" }],
      explanation: "Concurrent access issue",
      suggested_fix: "Add mutex",
    };
    const result = renderLineComment(issue);
    expect(result).toContain("\u{1F7E0}"); // Orange circle emoji
  });

  it("includes severity emoji for MEDIUM", () => {
    const issue: ReviewIssue = {
      title: "Inefficient loop",
      severity: "MEDIUM",
      category: "PERFORMANCE",
      location: [{ filename: "src/loop.py" }],
      explanation: "O(n^2) complexity",
      suggested_fix: "Use a set",
    };
    const result = renderLineComment(issue);
    expect(result).toContain("\u{1F7E1}"); // Yellow circle emoji
  });

  it("includes severity emoji for LOW", () => {
    const issue: ReviewIssue = {
      title: "Missing docstring",
      severity: "LOW",
      category: "DOCUMENTATION",
      location: [{ filename: "src/utils.py" }],
      explanation: "Function lacks documentation",
      suggested_fix: "Add docstring",
    };
    const result = renderLineComment(issue);
    expect(result).toContain("\u{1F7E2}"); // Green circle emoji
  });

  it("includes confidence when present", () => {
    const issue: ReviewIssue = {
      title: "Potential bug",
      severity: "HIGH",
      category: "LOGIC",
      location: [{ filename: "src/main.py" }],
      explanation: "Something looks wrong",
      suggested_fix: "Fix it",
      confidence: 8,
      rationale: "Code clearly shows the issue",
    };
    const result = renderLineComment(issue);
    expect(result).toContain("**Confidence:** 8/10");
    expect(result).toContain("Code clearly shows the issue");
  });

  it("shows other locations when multiple", () => {
    const issue: ReviewIssue = {
      title: "Duplicated code",
      severity: "MEDIUM",
      category: "QUALITY",
      location: [
        { filename: "src/a.py", line: 10 },
        { filename: "src/b.py", line: 20 },
        { filename: "src/c.py" },
      ],
      explanation: "Code is duplicated",
      suggested_fix: "Extract to common function",
    };
    const result = renderLineComment(issue);
    expect(result).toContain("**Also affects:**");
    expect(result).toContain("`src/b.py:20`");
    expect(result).toContain("`src/c.py`");
  });
});

describe("renderSummaryComment", () => {
  it("includes marker", () => {
    const output: ReviewOutput = {
      description: "Overall the code looks good",
      issues: [],
    };
    const result = renderSummaryComment(output);
    expect(result).toContain(MARKER_SUMMARY);
  });

  it("shows no issues message when empty", () => {
    const output: ReviewOutput = {
      description: "No problems found",
      issues: [],
    };
    const result = renderSummaryComment(output);
    expect(result).toContain("\u{2705} No issues found");
  });

  it("renders issues table", () => {
    const output: ReviewOutput = {
      description: "Found some issues",
      issues: [
        {
          title: "Bug found",
          severity: "HIGH",
          category: "LOGIC",
          location: [{ filename: "src/main.py" }],
          explanation: "There is a bug",
          suggested_fix: "Fix the bug",
        },
      ],
    };
    const result = renderSummaryComment(output);
    expect(result).toContain("| # | Title | Category | Severity | Location |");
    expect(result).toContain("Bug found");
    expect(result).toContain("`src/main.py`");
  });

  it("shows location count for multiple locations", () => {
    const output: ReviewOutput = {
      description: "Found some issues",
      issues: [
        {
          title: "Duplicated",
          severity: "MEDIUM",
          category: "QUALITY",
          location: [
            { filename: "src/a.py" },
            { filename: "src/b.py" },
            { filename: "src/c.py" },
          ],
          explanation: "Code duplicated",
          suggested_fix: "Extract",
        },
      ],
    };
    const result = renderSummaryComment(output);
    expect(result).toContain("`src/a.py (+2)`");
  });

  it("includes footer link", () => {
    const output: ReviewOutput = {
      description: "Test",
      issues: [],
    };
    const result = renderSummaryComment(output);
    expect(result).toContain("ReviewCerberus");
    expect(result).toContain("github.com/Kirill89/reviewcerberus");
  });
});

describe("sortIssuesBySeverity", () => {
  it("sorts CRITICAL first", () => {
    const issues: ReviewIssue[] = [
      {
        title: "Low",
        severity: "LOW",
        category: "DOCUMENTATION",
        location: [{ filename: "a.py" }],
        explanation: "",
        suggested_fix: "",
      },
      {
        title: "Critical",
        severity: "CRITICAL",
        category: "SECURITY",
        location: [{ filename: "b.py" }],
        explanation: "",
        suggested_fix: "",
      },
      {
        title: "Medium",
        severity: "MEDIUM",
        category: "QUALITY",
        location: [{ filename: "c.py" }],
        explanation: "",
        suggested_fix: "",
      },
    ];
    const sorted = sortIssuesBySeverity(issues);
    expect(sorted[0].severity).toBe("CRITICAL");
    expect(sorted[1].severity).toBe("MEDIUM");
    expect(sorted[2].severity).toBe("LOW");
  });

  it("maintains order for same severity", () => {
    const issues: ReviewIssue[] = [
      {
        title: "First HIGH",
        severity: "HIGH",
        category: "LOGIC",
        location: [{ filename: "a.py" }],
        explanation: "",
        suggested_fix: "",
      },
      {
        title: "Second HIGH",
        severity: "HIGH",
        category: "LOGIC",
        location: [{ filename: "b.py" }],
        explanation: "",
        suggested_fix: "",
      },
    ];
    const sorted = sortIssuesBySeverity(issues);
    expect(sorted[0].title).toBe("First HIGH");
    expect(sorted[1].title).toBe("Second HIGH");
  });

  it("does not mutate original array", () => {
    const issues: ReviewIssue[] = [
      {
        title: "Low",
        severity: "LOW",
        category: "DOCUMENTATION",
        location: [{ filename: "a.py" }],
        explanation: "",
        suggested_fix: "",
      },
      {
        title: "Critical",
        severity: "CRITICAL",
        category: "SECURITY",
        location: [{ filename: "b.py" }],
        explanation: "",
        suggested_fix: "",
      },
    ];
    sortIssuesBySeverity(issues);
    expect(issues[0].severity).toBe("LOW");
  });
});
