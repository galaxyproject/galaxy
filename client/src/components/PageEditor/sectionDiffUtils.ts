/**
 * Markdown heading-based section splitting + jsdiff utilities for
 * page agent edit proposals (Mode 1: full replacement, Mode 2: section patch).
 */
import { type Change, diffLines } from "diff";

/** A contiguous block of markdown delimited by headings. */
export interface MarkdownSection {
    /** The heading text including `#` prefix, or "" for the preamble before the first heading. */
    heading: string;
    /** 0-based line index where this section starts in the original document. */
    startLine: number;
    /** 0-based line index of the last line of this section (inclusive). */
    endLine: number;
    /** Full text of the section including its heading line. */
    content: string;
}

/** A per-section diff result pairing a section with its line-level changes. */
export interface SectionChange {
    /** The section from the *old* document (null if section was added). */
    oldSection: MarkdownSection | null;
    /** The section from the *new* document (null if section was removed). */
    newSection: MarkdownSection | null;
    /** Line-level diff changes for this section. */
    changes: Change[];
    /** Whether this section has any actual modifications. */
    hasChanges: boolean;
}

const HEADING_RE = /^#{1,6}\s/;

/**
 * Split markdown into sections delimited by headings.
 * Content before the first heading becomes a "preamble" section with heading "".
 */
export function markdownSections(content: string): MarkdownSection[] {
    if (!content) {
        return [];
    }

    const lines = content.split("\n");
    const sections: MarkdownSection[] = [];
    let currentHeading = "";
    let currentStartLine = 0;
    let currentLines: string[] = [];

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i]!;
        if (HEADING_RE.test(line) && i > 0) {
            // Flush previous section
            sections.push({
                heading: currentHeading,
                startLine: currentStartLine,
                endLine: i - 1,
                content: currentLines.join("\n"),
            });
            currentHeading = line;
            currentStartLine = i;
            currentLines = [line];
        } else if (HEADING_RE.test(line) && i === 0) {
            currentHeading = line;
            currentLines = [line];
        } else {
            currentLines.push(line);
        }
    }

    // Flush last section
    if (currentLines.length > 0) {
        sections.push({
            heading: currentHeading,
            startLine: currentStartLine,
            endLine: lines.length - 1,
            content: currentLines.join("\n"),
        });
    }

    return sections;
}

/**
 * Compute a line-level diff between two strings, returned as jsdiff `Change[]`.
 * Thin wrapper around `diffLines` for consistent options.
 */
export function computeLineDiff(oldText: string, newText: string): Change[] {
    return diffLines(oldText, newText, { newlineIsToken: false });
}

/**
 * Compute per-section diffs between old and new document content.
 * Sections are matched by heading text (case-sensitive exact match).
 */
export function sectionDiff(oldContent: string, newContent: string): SectionChange[] {
    const oldSections = markdownSections(oldContent);
    const newSections = markdownSections(newContent);

    const oldByHeading = new Map<string, MarkdownSection>();
    for (const s of oldSections) {
        oldByHeading.set(s.heading, s);
    }

    const newByHeading = new Map<string, MarkdownSection>();
    for (const s of newSections) {
        newByHeading.set(s.heading, s);
    }

    const result: SectionChange[] = [];
    const seen = new Set<string>();

    // Walk new sections in order — matched or added
    for (const ns of newSections) {
        seen.add(ns.heading);
        const os = oldByHeading.get(ns.heading) ?? null;
        const oldText = os ? os.content + "\n" : "";
        const newText = ns.content + "\n";
        const changes = computeLineDiff(oldText, newText);
        const hasChanges = os === null || os.content !== ns.content;
        result.push({ oldSection: os, newSection: ns, changes, hasChanges });
    }

    // Removed sections (in old but not in new)
    for (const os of oldSections) {
        if (!seen.has(os.heading)) {
            const changes = computeLineDiff(os.content + "\n", "");
            result.push({ oldSection: os, newSection: null, changes, hasChanges: true });
        }
    }

    return result;
}

/**
 * Apply only the accepted section changes to produce a new document.
 *
 * @param oldContent   The original document text.
 * @param newContent   The fully-proposed new document text.
 * @param acceptedHeadings  Set of heading strings whose changes should be applied.
 * @returns  The merged document with only accepted sections changed.
 */
export function applySectionPatches(oldContent: string, newContent: string, acceptedHeadings: Set<string>): string {
    const oldSections = markdownSections(oldContent);
    const newSections = markdownSections(newContent);

    const newByHeading = new Map<string, MarkdownSection>();
    for (const s of newSections) {
        newByHeading.set(s.heading, s);
    }

    const oldHeadings = new Set(oldSections.map((s) => s.heading));

    // Build result by walking old sections, replacing accepted ones
    const parts: string[] = [];
    for (const os of oldSections) {
        if (acceptedHeadings.has(os.heading) && newByHeading.has(os.heading)) {
            parts.push(newByHeading.get(os.heading)!.content);
        } else {
            parts.push(os.content);
        }
    }

    // Append newly-added sections that were accepted
    for (const ns of newSections) {
        if (!oldHeadings.has(ns.heading) && acceptedHeadings.has(ns.heading)) {
            parts.push(ns.content);
        }
    }

    return parts.join("\n");
}

/**
 * Reconstruct a full proposed document by replacing a single section.
 * Used for section_patch mode where the agent provides a target heading + new content.
 */
export function applySectionEdit(originalContent: string, targetHeading: string, newSectionContent: string): string {
    const sections = markdownSections(originalContent);
    const parts: string[] = [];
    let found = false;

    for (const s of sections) {
        if (s.heading === targetHeading) {
            parts.push(newSectionContent);
            found = true;
        } else {
            parts.push(s.content);
        }
    }

    // If heading not found, append as new section
    if (!found) {
        parts.push(newSectionContent);
    }

    return parts.join("\n");
}

/** Summary stats for a diff. */
export interface DiffStats {
    additions: number;
    deletions: number;
}

/** Count added/removed lines from a Change array. */
export function diffStats(changes: Change[]): DiffStats {
    let additions = 0;
    let deletions = 0;
    for (const c of changes) {
        const lineCount = c.count ?? 0;
        if (c.added) {
            additions += lineCount;
        } else if (c.removed) {
            deletions += lineCount;
        }
    }
    return { additions, deletions };
}
