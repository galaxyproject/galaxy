import { describe, expect, it } from "vitest";

import { jobsFilterParams } from "./JobsFilters";

describe("jobsFilterParams", () => {
    it("puts unspecified text into search with tool ID", () => {
        expect(jobsFilterParams("grep1")).toEqual({ search: "tool:grep1" });
    });

    it("puts tool_id: into search as tool:, not its own param", () => {
        expect(jobsFilterParams("tool_id:foo")).toEqual({ search: "tool:foo" });
    });

    it("keeps unspecified text alongside tool ID: in search", () => {
        expect(jobsFilterParams("grep1 tool_id:foo")).toEqual({ search: "tool:foo grep1" });
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
        expect(jobsFilterParams("grep1 tool_id:foo state:ok")).toEqual({
            state: ["ok"],
            search: "tool:foo grep1",
        });
    });

    it("returns an empty object for empty filterText", () => {
        expect(jobsFilterParams("")).toEqual({});
    });

    it("keeps a free text quoted value quoted and case-preserved in search", () => {
        expect(jobsFilterParams("'Grep1'")).toEqual({ search: "tool:'Grep1'" });
    });

    it("keeps explicitly quoted tool_id_eq values quoted and case-preserved in search", () => {
        expect(jobsFilterParams("tool_id_eq:'Grep1'")).toEqual({ search: "tool:'Grep1'" });
    });

    it("preserves case for an unquoted tool_id_eq value in search", () => {
        // tool_id_eq is itself an exact-match key, so it doesn't need quoting to keep its case
        expect(jobsFilterParams("tool_id_eq:Grep1")).toEqual({ search: "tool:'Grep1'" });
    });

    it("lowercases and does not quote an unquoted tool_id value", () => {
        expect(jobsFilterParams("tool_id:Grep1")).toEqual({ search: "tool:grep1" });
    });

    it("doesn't combine a quoted tool_id value alongside unspecified text", () => {
        expect(jobsFilterParams("grep1 tool_id:'Grep1'")).toEqual({ search: "tool:Grep1 grep1" });
    });
});
