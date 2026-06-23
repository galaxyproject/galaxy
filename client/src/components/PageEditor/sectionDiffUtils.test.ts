import { describe, expect, it } from "vitest";

import {
    applySectionEdit,
    applySectionPatches,
    computeLineDiff,
    diffStats,
    markdownSections,
    sectionDiff,
} from "./sectionDiffUtils";

// ---------------------------------------------------------------------------
// markdownSections
// ---------------------------------------------------------------------------
describe("markdownSections", () => {
    it("returns empty array for empty string", () => {
        expect(markdownSections("")).toEqual([]);
    });

    it("returns single preamble section when no headings", () => {
        const sections = markdownSections("Hello world\nSecond line");
        expect(sections).toHaveLength(1);
        expect(sections[0]!.heading).toBe("");
        expect(sections[0]!.content).toBe("Hello world\nSecond line");
        expect(sections[0]!.startLine).toBe(0);
        expect(sections[0]!.endLine).toBe(1);
    });

    it("splits on h1 headings", () => {
        const doc = "# Intro\nSome text\n# Methods\nMore text";
        const sections = markdownSections(doc);
        expect(sections).toHaveLength(2);
        expect(sections[0]!.heading).toBe("# Intro");
        expect(sections[0]!.content).toBe("# Intro\nSome text");
        expect(sections[1]!.heading).toBe("# Methods");
        expect(sections[1]!.content).toBe("# Methods\nMore text");
    });

    it("splits on mixed heading levels", () => {
        const doc = "# Title\nText\n## Sub\nMore\n### Deep\nDeep text";
        const sections = markdownSections(doc);
        expect(sections).toHaveLength(3);
        expect(sections[0]!.heading).toBe("# Title");
        expect(sections[1]!.heading).toBe("## Sub");
        expect(sections[2]!.heading).toBe("### Deep");
    });

    it("handles preamble before first heading", () => {
        const doc = "Some preamble\n\n# First Heading\nContent";
        const sections = markdownSections(doc);
        expect(sections).toHaveLength(2);
        expect(sections[0]!.heading).toBe("");
        expect(sections[0]!.content).toBe("Some preamble\n");
        expect(sections[1]!.heading).toBe("# First Heading");
    });

    it("handles single heading with no body", () => {
        const sections = markdownSections("# Just a heading");
        expect(sections).toHaveLength(1);
        expect(sections[0]!.heading).toBe("# Just a heading");
        expect(sections[0]!.content).toBe("# Just a heading");
    });

    it("does not split on non-heading hash lines", () => {
        // Lines like "##notaheading" (no space) should not split
        const doc = "# Real\nText\n##notaheading\nMore";
        const sections = markdownSections(doc);
        expect(sections).toHaveLength(1);
        expect(sections[0]!.content).toContain("##notaheading");
    });

    it("handles h6 headings", () => {
        const doc = "###### Deep heading\nContent";
        const sections = markdownSections(doc);
        expect(sections).toHaveLength(1);
        expect(sections[0]!.heading).toBe("###### Deep heading");
    });

    it("tracks correct line numbers", () => {
        const doc = "# A\nline1\nline2\n# B\nline3";
        const sections = markdownSections(doc);
        expect(sections[0]!.startLine).toBe(0);
        expect(sections[0]!.endLine).toBe(2);
        expect(sections[1]!.startLine).toBe(3);
        expect(sections[1]!.endLine).toBe(4);
    });
});

// ---------------------------------------------------------------------------
// computeLineDiff
// ---------------------------------------------------------------------------
describe("computeLineDiff", () => {
    it("returns no changes for identical text", () => {
        const changes = computeLineDiff("hello\n", "hello\n");
        expect(changes).toHaveLength(1);
        expect(changes[0]!.added).toBeFalsy();
        expect(changes[0]!.removed).toBeFalsy();
    });

    it("detects added lines", () => {
        const changes = computeLineDiff("a\n", "a\nb\n");
        const added = changes.filter((c) => c.added);
        expect(added.length).toBeGreaterThan(0);
    });

    it("detects removed lines", () => {
        const changes = computeLineDiff("a\nb\n", "a\n");
        const removed = changes.filter((c) => c.removed);
        expect(removed.length).toBeGreaterThan(0);
    });
});

// ---------------------------------------------------------------------------
// diffStats
// ---------------------------------------------------------------------------
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

// ---------------------------------------------------------------------------
// sectionDiff
// ---------------------------------------------------------------------------
describe("sectionDiff", () => {
    it("detects no changes for identical docs", () => {
        const doc = "# A\ntext\n# B\nmore";
        const result = sectionDiff(doc, doc);
        expect(result.every((s) => !s.hasChanges)).toBe(true);
    });

    it("detects modified section", () => {
        const old = "# A\nold text\n# B\nkept";
        const updated = "# A\nnew text\n# B\nkept";
        const result = sectionDiff(old, updated);
        const changed = result.filter((s) => s.hasChanges);
        expect(changed).toHaveLength(1);
        expect(changed[0]!.newSection!.heading).toBe("# A");
    });

    it("detects added section", () => {
        const old = "# A\ntext";
        const updated = "# A\ntext\n# B\nnew stuff";
        const result = sectionDiff(old, updated);
        const added = result.filter((s) => s.oldSection === null);
        expect(added).toHaveLength(1);
        expect(added[0]!.newSection!.heading).toBe("# B");
        expect(added[0]!.hasChanges).toBe(true);
    });

    it("detects removed section", () => {
        const old = "# A\ntext\n# B\nmore";
        const updated = "# A\ntext";
        const result = sectionDiff(old, updated);
        const removed = result.filter((s) => s.newSection === null);
        expect(removed).toHaveLength(1);
        expect(removed[0]!.oldSection!.heading).toBe("# B");
    });

    it("handles empty old document", () => {
        const result = sectionDiff("", "# New\ncontent");
        expect(result).toHaveLength(1);
        expect(result[0]!.oldSection).toBeNull();
        expect(result[0]!.hasChanges).toBe(true);
    });

    it("handles empty new document", () => {
        const result = sectionDiff("# Old\ncontent", "");
        expect(result).toHaveLength(1);
        expect(result[0]!.newSection).toBeNull();
        expect(result[0]!.hasChanges).toBe(true);
    });
});

// ---------------------------------------------------------------------------
// applySectionPatches
// ---------------------------------------------------------------------------
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
