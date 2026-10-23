import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import { type Tool, useToolStore } from "@/stores/toolStore";

import { jobsFilterParams, MAX_TOOL_NAME_MATCHES } from "./JobsFilters";

describe("jobsFilterParams", () => {
    describe("search by id mode", () => {
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

        it("lowercases an unquoted mixed-case state value to match the backend's stored values", () => {
            expect(jobsFilterParams("state:OK")).toEqual({ state: ["ok"] });
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

        it("throws instead of silently dropping an invalid filter key", () => {
            expect(() => jobsFilterParams("xx:ss")).toThrow("Invalid filter(s) in query: xx");
        });
    });

    describe("search by name mode", () => {
        beforeEach(() => {
            setActivePinia(createPinia());
            useToolStore().saveAllTools([
                { id: "cut1", name: "Cut" },
                { id: "adv_cut1", name: "Advanced Cut" },
            ] as unknown as Tool[]);
        });

        it("matches all tools whose name contains the unspecified text", () => {
            expect(jobsFilterParams("cut", true).tool_id?.sort()).toEqual(["adv_cut1", "cut1"]);
        });

        it("matches only tools whose name contains an explicit name: value", () => {
            expect(jobsFilterParams("name:advanced", true)).toEqual({ tool_id: ["adv_cut1"] });
        });

        it("is case-insensitive for a partial match", () => {
            expect(jobsFilterParams("CUT", true).tool_id?.sort()).toEqual(["adv_cut1", "cut1"]);
        });

        it("matches only the exact tool for a quoted, unspecified name", () => {
            expect(jobsFilterParams("'Cut'", true)).toEqual({ tool_id: ["cut1"] });
        });

        it("matches only the exact tool for an explicit quoted name_eq:", () => {
            expect(jobsFilterParams("name_eq:'Cut'", true)).toEqual({ tool_id: ["cut1"] });
        });

        it("is case-insensitive for an exact match too", () => {
            expect(jobsFilterParams("'CUT'", true)).toEqual({ tool_id: ["cut1"] });
        });

        it("throws an error when no tool name matches", () => {
            expect(() => jobsFilterParams("nonexistent-tool", true)).toThrow(
                `No tools matched the provided name: nonexistent-tool`,
            );
        });

        it("throws instead of sending an unbounded tool_id list", () => {
            const tools = Array.from({ length: MAX_TOOL_NAME_MATCHES + 1 }, (_, i) => ({
                id: `filter${i}`,
                name: `Filter ${i}`,
            }));
            useToolStore().saveAllTools(tools as unknown as Tool[]);
            expect(jobsFilterParams("'Filter 1'", true)).toEqual({ tool_id: ["filter1"] });
            expect(() => jobsFilterParams("filter", true)).toThrow(
                `${MAX_TOOL_NAME_MATCHES + 1} tools matched the provided name: filter. Please refine your search.`,
            );
        });

        it("combines a name filter with state, out of search", () => {
            const params = jobsFilterParams("cut state:ok", true);
            expect(params.state).toEqual(["ok"]);
            expect(params.tool_id?.sort()).toEqual(["adv_cut1", "cut1"]);
            expect(Object.keys(params).sort()).toEqual(["state", "tool_id"]);
        });

        it("does not set tool_id when no name text is present", () => {
            expect(jobsFilterParams("state:ok", true)).toEqual({ state: ["ok"] });
        });
    });
});
