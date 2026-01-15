import { describe, it, expect } from "vitest";
import { filterByConfidence, parseReviewOutput } from "../src/review";
import { ReviewIssue } from "../src/types";

describe("filterByConfidence", () => {
  const makeIssue = (
    title: string,
    confidence?: number | null
  ): ReviewIssue => ({
    title,
    severity: "HIGH",
    category: "LOGIC",
    location: [{ filename: "test.py" }],
    explanation: "Test explanation",
    suggested_fix: "Test fix",
    confidence,
  });

  it("filters issues below threshold", () => {
    const issues = [makeIssue("A", 8), makeIssue("B", 5), makeIssue("C", 9)];
    const result = filterByConfidence(issues, 7);
    expect(result).toHaveLength(2);
    expect(result.map((i) => i.title)).toEqual(["A", "C"]);
  });

  it("returns all issues when no threshold", () => {
    const issues = [makeIssue("A", 3), makeIssue("B", 5)];
    expect(filterByConfidence(issues, undefined)).toHaveLength(2);
  });

  it("includes issues at exactly the threshold", () => {
    const issues = [makeIssue("A", 7), makeIssue("B", 6)];
    const result = filterByConfidence(issues, 7);
    expect(result).toHaveLength(1);
    expect(result[0].title).toBe("A");
  });

  it("includes issues without confidence (unverified)", () => {
    const issues = [
      makeIssue("A", 8),
      makeIssue("B", undefined),
      makeIssue("C", null),
    ];
    const result = filterByConfidence(issues, 7);
    expect(result).toHaveLength(3);
  });

  it("returns empty array when all filtered", () => {
    const issues = [makeIssue("A", 3), makeIssue("B", 2)];
    const result = filterByConfidence(issues, 10);
    expect(result).toHaveLength(0);
  });

  it("handles empty array", () => {
    const result = filterByConfidence([], 5);
    expect(result).toHaveLength(0);
  });
});

describe("parseReviewOutput", () => {
  it("parses valid JSON output", () => {
    const json = JSON.stringify({
      description: "Test description",
      issues: [
        {
          title: "Test issue",
          category: "LOGIC",
          severity: "HIGH",
          location: [{ filename: "test.py", line: 10 }],
          explanation: "Test explanation",
          suggested_fix: "Test fix",
        },
      ],
    });

    const result = parseReviewOutput(json);
    expect(result.description).toBe("Test description");
    expect(result.issues).toHaveLength(1);
    expect(result.issues[0].title).toBe("Test issue");
    expect(result.issues[0].location[0].filename).toBe("test.py");
    expect(result.issues[0].location[0].line).toBe(10);
  });

  it("parses output with no issues", () => {
    const json = JSON.stringify({
      description: "No issues found",
      issues: [],
    });

    const result = parseReviewOutput(json);
    expect(result.description).toBe("No issues found");
    expect(result.issues).toHaveLength(0);
  });

  it("parses output with verification data", () => {
    const json = JSON.stringify({
      description: "Verified review",
      issues: [
        {
          title: "Verified issue",
          category: "SECURITY",
          severity: "CRITICAL",
          location: [{ filename: "secure.py" }],
          explanation: "Security issue",
          suggested_fix: "Fix it",
          confidence: 9,
          rationale: "Clear evidence in code",
        },
      ],
    });

    const result = parseReviewOutput(json);
    expect(result.issues[0].confidence).toBe(9);
    expect(result.issues[0].rationale).toBe("Clear evidence in code");
  });

  it("parses output with multiple locations", () => {
    const json = JSON.stringify({
      description: "Test",
      issues: [
        {
          title: "Multi-location issue",
          category: "QUALITY",
          severity: "MEDIUM",
          location: [
            { filename: "a.py", line: 1 },
            { filename: "b.py", line: 2 },
            { filename: "c.py" },
          ],
          explanation: "Issue in multiple places",
          suggested_fix: "Fix all",
        },
      ],
    });

    const result = parseReviewOutput(json);
    expect(result.issues[0].location).toHaveLength(3);
    expect(result.issues[0].location[0].line).toBe(1);
    expect(result.issues[0].location[2].line).toBeUndefined();
  });
});
