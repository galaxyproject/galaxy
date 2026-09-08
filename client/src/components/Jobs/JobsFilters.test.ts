import { describe, expect, it } from "vitest";

import { jobsFilterParams } from "./JobsFilters";

describe("jobsFilterParams", () => {
    it("puts unspecified text into search", () => {
        expect(jobsFilterParams("grep1")).toEqual({ search: "grep1" });
    });

    it("puts tool: into search, not its own param", () => {
        expect(jobsFilterParams("tool:foo")).toEqual({ search: "tool:foo" });
    });

    it("keeps unspecified text alongside tool: in search", () => {
        expect(jobsFilterParams("grep1 tool:foo")).toEqual({ search: "tool:foo grep1" });
    });

    it("does not leak unspecified_text: into search", () => {
        // unspecified text must stay unlabeled, not "unspecified_text:grep1"
        expect(jobsFilterParams("grep1").search).not.toContain("unspecified_text");
    });

    it("pulls state into its own param, out of search", () => {
        expect(jobsFilterParams("state:ok")).toEqual({ state: ["ok"] });
    });

    it("pulls update_time range into its own params, out of search", () => {
        expect(jobsFilterParams("update_time>'2024-01-01' update_time<'2024-02-01'")).toEqual({
            date_range_min: "2024-01-01",
            date_range_max: "2024-02-01",
        });
    });

    it("combines dedicated params with search", () => {
        expect(jobsFilterParams("grep1 tool:foo state:ok")).toEqual({
            state: ["ok"],
            search: "tool:foo grep1",
        });
    });

    it("returns an empty object for empty filterText", () => {
        expect(jobsFilterParams("")).toEqual({});
    });

    it("keeps a quoted tool: value quoted and case-preserved in search", () => {
        expect(jobsFilterParams("tool:'Grep1'")).toEqual({ search: "tool:'Grep1'" });
    });

    it("lowercases and does not quote an unquoted tool: value", () => {
        expect(jobsFilterParams("tool:Grep1")).toEqual({ search: "tool:grep1" });
    });

    it("keeps a quoted tool: value alongside unspecified text", () => {
        expect(jobsFilterParams("grep1 tool:'Grep1'")).toEqual({ search: "tool:'Grep1' grep1" });
    });
});
