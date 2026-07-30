import { describe, expect, it } from "vitest";

import { getArgs, parseMarkdown, referencedObjects, replaceLabel, splitMarkdown } from "./parse";

describe("parseMarkdown", () => {
    it("returns a single markdown section for plain text", () => {
        expect(parseMarkdown("hello\nworld")).toEqual([{ name: "markdown", content: "hello\nworld" }]);
    });

    it("splits fenced blocks by their tag", () => {
        const md = "# Title\n```galaxy\njob_metrics(job_id=j1)\n```\nafter";
        expect(parseMarkdown(md)).toEqual([
            { name: "markdown", content: "# Title" },
            { name: "galaxy", content: "job_metrics(job_id=j1)" },
            { name: "markdown", content: "after" },
        ]);
    });

    it("recognizes non-galaxy fenced blocks (visualization, vega)", () => {
        const md = '```vega\n{"mark":"bar"}\n```';
        expect(parseMarkdown(md)).toEqual([{ name: "vega", content: '{"mark":"bar"}' }]);
    });
});

describe("getArgs", () => {
    it("parses a directive name and args", () => {
        const r = getArgs("job_metrics(job_id=j1)");
        expect(r.name).toBe("job_metrics");
        expect(r.args).toEqual({ job_id: "j1" });
    });

    it("parses multiple args and strips quotes", () => {
        const r = getArgs('visualization(visualization_id=igv, history_dataset_id=abc, title="my plot")');
        expect(r.name).toBe("visualization");
        expect(r.args).toEqual({ visualization_id: "igv", history_dataset_id: "abc", title: "my plot" });
    });

    it("keeps commas and equals inside quoted values", () => {
        expect(getArgs('job_metrics(title="a, b")').args).toEqual({ title: "a, b" });
        expect(getArgs('job_metrics(expr="a=b")').args).toEqual({ expr: "a=b" });
    });

    it("throws on non-directive content", () => {
        expect(() => getArgs("not a directive")).toThrow();
    });
});

describe("splitMarkdown", () => {
    it("extracts galaxy directive sections with parsed args", () => {
        const { sections } = splitMarkdown("A\n```galaxy\njob_metrics(job_id=j1)\n```\nB");
        const directive = sections.find((s) => "args" in s) as { name: string; args: Record<string, string> } | undefined;
        expect(directive?.name).toBe("job_metrics");
        expect(directive?.args).toEqual({ job_id: "j1" });
    });

    it("does not recognize visualization blocks as directives (current limitation)", () => {
        const { sections } = splitMarkdown('```visualization\n{"dataset_id":"abc"}\n```');
        expect(sections.every((s) => !("args" in s))).toBe(true);
    });
});

describe("referencedObjects", () => {
    it("collects ids from galaxy directive args", () => {
        const md = "```galaxy\nhistory_dataset_display(history_dataset_id=d1)\n```";
        const refs = referencedObjects(md);
        expect([...refs.historyDatasets]).toEqual(["d1"]);
    });

    // Desired post-unification behavior: viz-block dataset bindings must be
    // collected so ObjectPermissions grants access to them. Red before the fix.
    it("collects datasets referenced inside visualization blocks", () => {
        const md = '```visualization\n{"visualization_name":"igv","dataset_id":"d2"}\n```';
        const refs = referencedObjects(md);
        expect([...refs.historyDatasets]).toContain("d2");
    });
});

describe("replaceLabel", () => {
    it("rewrites a matching workflow input label in a directive", () => {
        const md = "```galaxy\nhistory_dataset_display(input=old)\n```";
        const out = replaceLabel(md, "input", "old", "new");
        expect(out).toContain("input=new");
    });

    it("leaves non-matching labels untouched", () => {
        const md = "```galaxy\nhistory_dataset_display(input=keep)\n```";
        const out = replaceLabel(md, "input", "other", "new");
        expect(out).toContain("input=keep");
    });

    it("quotes a replacement label containing a space", () => {
        const md = "```galaxy\nhistory_dataset_display(input=old)\n```";
        const out = replaceLabel(md, "input", "old", "new label");
        expect(out).toContain("input='new label'");
    });
});
