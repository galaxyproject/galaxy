import { nth } from "@tests/vitest/helpers";
import { describe, expect, it } from "vitest";

import {
    applySectionEdit,
    applySectionPatches,
    computeLineDiff,
    diffStats,
    markdownSections,
    sectionDiff,
} from "./sectionDiffUtils";

describe("markdownSections", () => {
    it("returns empty array for empty string", () => {
        expect(markdownSections("")).toEqual([]);
    });

    it("returns single preamble section when no headings", () => {
        const sections = markdownSections("Hello world\nSecond line");
        expect(sections).toHaveLength(1);
        const firstSection = nth(sections, 0);
        expect(firstSection.heading).toBe("");
        expect(firstSection.content).toBe("Hello world\nSecond line");
        expect(firstSection.startLine).toBe(0);
        expect(firstSection.endLine).toBe(1);
    });

    it("splits on h1 headings", () => {
        const markdown = "# Intro\nSome text\n# Methods\nMore text";
        const sections = markdownSections(markdown);
        expect(sections).toHaveLength(2);
        const firstSection = nth(sections, 0);
        const secondSection = nth(sections, 1);
        expect(firstSection.heading).toBe("# Intro");
        expect(firstSection.content).toBe("# Intro\nSome text");
        expect(secondSection.heading).toBe("# Methods");
        expect(secondSection.content).toBe("# Methods\nMore text");
    });

    it("splits on mixed heading levels", () => {
        const markdown = "# Title\nText\n## Sub\nMore\n### Deep\nDeep text";
        const sections = markdownSections(markdown);
        expect(sections).toHaveLength(3);
        const firstSection = nth(sections, 0);
        const secondSection = nth(sections, 1);
        const thirdSection = nth(sections, 2);
        expect(firstSection.heading).toBe("# Title");
        expect(secondSection.heading).toBe("## Sub");
        expect(thirdSection.heading).toBe("### Deep");
    });

    it("handles preamble before first heading", () => {
        const markdown = "Some preamble\n\n# First Heading\nContent";
        const sections = markdownSections(markdown);
        expect(sections).toHaveLength(2);
        const firstSection = nth(sections, 0);
        const secondSection = nth(sections, 1);
        expect(firstSection.heading).toBe("");
        expect(firstSection.content).toBe("Some preamble\n");
        expect(secondSection.heading).toBe("# First Heading");
    });

    it("handles single heading with no body", () => {
        const sections = markdownSections("# Just a heading");
        expect(sections).toHaveLength(1);
        const firstSection = nth(sections, 0);
        expect(firstSection.heading).toBe("# Just a heading");
        expect(firstSection.content).toBe("# Just a heading");
    });

    it("does not split on non-heading hash lines", () => {
        const markdown = "# Real\nText\n##notaheading\nMore";
        const sections = markdownSections(markdown);
        expect(sections).toHaveLength(1);
        const firstSection = nth(sections, 0);
        expect(firstSection.content).toContain("##notaheading");
    });

    it("handles h6 headings", () => {
        const markdown = "###### Deep heading\nContent";
        const sections = markdownSections(markdown);
        expect(sections).toHaveLength(1);
        const firstSection = nth(sections, 0);
        expect(firstSection.heading).toBe("###### Deep heading");
    });

    it("tracks correct line numbers", () => {
        const markdown = "# A\nline1\nline2\n# B\nline3";
        const sections = markdownSections(markdown);
        const firstSection = nth(sections, 0);
        const secondSection = nth(sections, 1);
        expect(firstSection.startLine).toBe(0);
        expect(firstSection.endLine).toBe(2);
        expect(secondSection.startLine).toBe(3);
        expect(secondSection.endLine).toBe(4);
    });
});

describe("computeLineDiff", () => {
    it("returns no changes for identical text", () => {
        const changes = computeLineDiff("hello\n", "hello\n");
        expect(changes).toHaveLength(1);
        expect(nth(changes, 0).added).toBeFalsy();
        expect(nth(changes, 0).removed).toBeFalsy();
    });

    it("detects added lines", () => {
        const changes = computeLineDiff("a\n", "a\nb\n");
        const added = changes.filter((change) => change.added);
        expect(added.length).toBeGreaterThan(0);
    });

    it("detects removed lines", () => {
        const changes = computeLineDiff("a\nb\n", "a\n");
        const removed = changes.filter((change) => change.removed);
        expect(removed.length).toBeGreaterThan(0);
    });
});

describe("diffStats", () => {
    it("counts additions and deletions", () => {
        const changes = computeLineDiff("line1\nline2\n", "line1\nline3\nline4\n");
        const stats = diffStats(changes);
        expect(stats.additions).toBeGreaterThan(0);
        expect(stats.deletions).toBeGreaterThan(0);
    });

    it("returns zeros for identical content", () => {
        const changes = computeLineDiff("same\n", "same\n");
        const stats = diffStats(changes);
        expect(stats.additions).toBe(0);
        expect(stats.deletions).toBe(0);
    });
});

describe("sectionDiff", () => {
    it("detects no changes for identical docs", () => {
        const markdown = "# A\ntext\n# B\nmore";
        const result = sectionDiff(markdown, markdown);
        expect(result.every((section) => !section.hasChanges)).toBe(true);
    });

    it("detects modified section", () => {
        const originalMarkdown = "# A\nold text\n# B\nkept";
        const proposedMarkdown = "# A\nnew text\n# B\nkept";
        const result = sectionDiff(originalMarkdown, proposedMarkdown);
        const changed = result.filter((section) => section.hasChanges);
        expect(changed).toHaveLength(1);
        expect(nth(changed, 0).newSection).toMatchObject({ heading: "# A" });
    });

    it("detects added section", () => {
        const originalMarkdown = "# A\ntext";
        const proposedMarkdown = "# A\ntext\n# B\nnew stuff";
        const result = sectionDiff(originalMarkdown, proposedMarkdown);
        const added = result.filter((section) => section.oldSection === null);
        expect(added).toHaveLength(1);
        expect(nth(added, 0).newSection).toMatchObject({ heading: "# B" });
        expect(nth(added, 0).hasChanges).toBe(true);
    });

    it("detects removed section", () => {
        const originalMarkdown = "# A\ntext\n# B\nmore";
        const proposedMarkdown = "# A\ntext";
        const result = sectionDiff(originalMarkdown, proposedMarkdown);
        const removed = result.filter((section) => section.newSection === null);
        expect(removed).toHaveLength(1);
        expect(nth(removed, 0).oldSection).toMatchObject({ heading: "# B" });
    });

    it("handles empty old document", () => {
        const result = sectionDiff("", "# New\ncontent");
        expect(result).toHaveLength(1);
        expect(nth(result, 0).oldSection).toBeNull();
        expect(nth(result, 0).hasChanges).toBe(true);
    });

    it("handles empty new document", () => {
        const result = sectionDiff("# Old\ncontent", "");
        expect(result).toHaveLength(1);
        expect(nth(result, 0).newSection).toBeNull();
        expect(nth(result, 0).hasChanges).toBe(true);
    });
});

describe("applySectionPatches", () => {
    const oldDoc = "# Intro\nOld intro\n# Methods\nOld methods\n# Results\nOld results";
    const newDoc = "# Intro\nNew intro\n# Methods\nNew methods\n# Results\nNew results";

    it("applies all sections when all accepted", () => {
        const accepted = new Set(["# Intro", "# Methods", "# Results"]);
        const result = applySectionPatches(oldDoc, newDoc, accepted);
        expect(result).toContain("New intro");
        expect(result).toContain("New methods");
        expect(result).toContain("New results");
        expect(result).not.toContain("Old");
    });

    it("applies no sections when none accepted", () => {
        const accepted = new Set<string>();
        const result = applySectionPatches(oldDoc, newDoc, accepted);
        expect(result).toContain("Old intro");
        expect(result).toContain("Old methods");
        expect(result).toContain("Old results");
        expect(result).not.toContain("New");
    });

    it("applies only accepted sections", () => {
        const accepted = new Set(["# Methods"]);
        const result = applySectionPatches(oldDoc, newDoc, accepted);
        expect(result).toContain("Old intro");
        expect(result).toContain("New methods");
        expect(result).toContain("Old results");
    });

    it("includes newly-added sections when accepted", () => {
        const newWithExtra = newDoc + "\n# Discussion\nNew discussion";
        const accepted = new Set(["# Discussion"]);
        const result = applySectionPatches(oldDoc, newWithExtra, accepted);
        expect(result).toContain("Old intro");
        expect(result).toContain("New discussion");
    });

    it("does not include newly-added sections when not accepted", () => {
        const newWithExtra = newDoc + "\n# Discussion\nNew discussion";
        const accepted = new Set<string>();
        const result = applySectionPatches(oldDoc, newWithExtra, accepted);
        expect(result).not.toContain("Discussion");
    });

    it("handles preamble section", () => {
        const oldWithPreamble = "Preamble text\n# Heading\nBody";
        const newWithPreamble = "New preamble\n# Heading\nBody";
        const accepted = new Set([""]);
        const result = applySectionPatches(oldWithPreamble, newWithPreamble, accepted);
        expect(result).toContain("New preamble");
    });
});

describe("applySectionEdit", () => {
    it("replaces matching section", () => {
        const original = "# Intro\nOld intro\n# Methods\nOld methods";
        const result = applySectionEdit(original, "# Methods", "# Methods\nNew methods");
        expect(result).toContain("# Intro\nOld intro");
        expect(result).toContain("# Methods\nNew methods");
        expect(result).not.toContain("Old methods");
    });

    it("appends new section if heading not found", () => {
        const original = "# Intro\nSome text";
        const result = applySectionEdit(original, "# Results", "# Results\nNew results");
        expect(result).toContain("# Intro\nSome text");
        expect(result).toContain("# Results\nNew results");
    });

    it("replaces preamble when heading is empty", () => {
        const original = "Preamble\n# A\nBody";
        const result = applySectionEdit(original, "", "New preamble");
        expect(result).toContain("New preamble");
        expect(result).toContain("# A\nBody");
        expect(result).not.toContain("Preamble\n# A");
    });
});
