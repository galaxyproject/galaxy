import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import type { JobBaseModel } from "@/api/jobs";
import { type Tool, useToolStore } from "@/stores/toolStore";

import { jobsFilterParams, JobsFiltersById, MAX_TOOL_NAME_MATCHES } from "./JobsFilters";

function buildJob(overrides: Partial<JobBaseModel> = {}): JobBaseModel {
    return {
        id: "job1",
        state: "ok",
        model_class: "Job",
        create_time: "2024-01-01T00:00:00",
        update_time: "2024-01-01T00:00:00",
        tool_id: "grep1",
        ...overrides,
    } as JobBaseModel;
}

describe("jobsFilterParams", () => {
    describe("search by id mode", () => {
        it("puts unspecified text into search with tool ID", () => {
            expect(jobsFilterParams("grep1").params).toEqual({ search: "tool:grep1" });
        });

        it("puts tool_id: into search as tool:, not its own param", () => {
            expect(jobsFilterParams("tool_id:foo").params).toEqual({ search: "tool:foo" });
        });

        it("keeps unspecified text alongside tool ID: in search", () => {
            expect(jobsFilterParams("grep1 tool_id:foo").params).toEqual({ search: "tool:foo grep1" });
        });

        it("pulls state into its own param, out of search", () => {
            expect(jobsFilterParams("state:ok").params).toEqual({ state: ["ok"] });
        });

        it("lowercases an unquoted mixed-case state value to match the backend's stored values", () => {
            expect(jobsFilterParams("state:OK").params).toEqual({ state: ["ok"] });
        });

        it("pulls update_time range into its own params, out of search", () => {
            expect(jobsFilterParams("update_time>'2024-01-01' update_time<'2024-02-01'").params).toEqual({
                date_range_min: "2024-01-01",
                date_range_max: "2024-02-01",
            });
        });

        it("combines dedicated params with search", () => {
            expect(jobsFilterParams("grep1 tool_id:foo state:ok").params).toEqual({
                state: ["ok"],
                search: "tool:foo grep1",
            });
        });

        it("returns an empty object for empty filterText", () => {
            expect(jobsFilterParams("").params).toEqual({});
        });

        it("keeps a free text quoted value quoted and case-preserved in search", () => {
            expect(jobsFilterParams("'Grep1'").params).toEqual({ search: "tool:'Grep1'" });
        });

        it("keeps explicitly quoted tool_id_eq values quoted and case-preserved in search", () => {
            expect(jobsFilterParams("tool_id_eq:'Grep1'").params).toEqual({ search: "tool:'Grep1'" });
        });

        it("preserves case for an unquoted tool_id_eq value in search", () => {
            // tool_id_eq is itself an exact-match key, so it doesn't need quoting to keep its case
            expect(jobsFilterParams("tool_id_eq:Grep1").params).toEqual({ search: "tool:'Grep1'" });
        });

        it("lowercases and does not quote an unquoted tool_id value", () => {
            expect(jobsFilterParams("tool_id:Grep1").params).toEqual({ search: "tool:grep1" });
        });

        it("doesn't combine a quoted tool_id value alongside unspecified text", () => {
            expect(jobsFilterParams("grep1 tool_id:'Grep1'").params).toEqual({ search: "tool:Grep1 grep1" });
        });

        it("throws instead of silently dropping an invalid filter key", () => {
            expect(() => jobsFilterParams("xx:ss")).toThrow("Invalid filter(s) in query: xx");
        });

        it("matchesJob ignores tool_id -- the backend's search decides that once, up front", () => {
            const { matchesJob } = jobsFilterParams("grep1");
            expect(matchesJob(buildJob({ tool_id: "unrelated_tool" }))).toBe(true);
        });

        it("matchesJob checks state", () => {
            const { matchesJob } = jobsFilterParams("state:queued");
            expect(matchesJob(buildJob({ state: "queued" }))).toBe(true);
            expect(matchesJob(buildJob({ state: "ok" }))).toBe(false);
        });

        it("matchesJob matches a quoted, case-preserved state value case-insensitively", () => {
            // state:'OK' keeps its quoted case ("OK"), but every job's state is always lowercase
            const { matchesJob } = jobsFilterParams("state:'OK'");
            expect(matchesJob(buildJob({ state: "ok" }))).toBe(true);
        });

        it("matchesJob matches everything when no filter text is given", () => {
            const { matchesJob } = jobsFilterParams("");
            expect(matchesJob(buildJob({ tool_id: "anything", state: "error" }))).toBe(true);
        });

        it("expands status into its member states, out of search", () => {
            expect(jobsFilterParams("status:problem").params).toEqual({ state: ["error", "failed"] });
        });

        it("status wins over a plain state value set at the same time", () => {
            expect(jobsFilterParams("state:ok status:problem").params).toEqual({ state: ["error", "failed"] });
        });

        it("matchesJob for status accepts any member state", () => {
            const { matchesJob } = jobsFilterParams("status:problem");
            expect(matchesJob(buildJob({ state: "error" }))).toBe(true);
            expect(matchesJob(buildJob({ state: "failed" }))).toBe(true);
            expect(matchesJob(buildJob({ state: "ok" }))).toBe(false);
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
            expect(jobsFilterParams("cut", true).params.tool_id?.sort()).toEqual(["adv_cut1", "cut1"]);
        });

        it("matches only tools whose name contains an explicit name: value", () => {
            expect(jobsFilterParams("name:advanced", true).params).toEqual({ tool_id: ["adv_cut1"] });
        });

        it("is case-insensitive for a partial match", () => {
            expect(jobsFilterParams("CUT", true).params.tool_id?.sort()).toEqual(["adv_cut1", "cut1"]);
        });

        it("matches only the exact tool for a quoted, unspecified name", () => {
            expect(jobsFilterParams("'Cut'", true).params).toEqual({ tool_id: ["cut1"] });
        });

        it("matches only the exact tool for an explicit quoted name_eq:", () => {
            expect(jobsFilterParams("name_eq:'Cut'", true).params).toEqual({ tool_id: ["cut1"] });
        });

        it("is case-insensitive for an exact match too", () => {
            expect(jobsFilterParams("'CUT'", true).params).toEqual({ tool_id: ["cut1"] });
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
            expect(jobsFilterParams("'Filter 1'", true).params).toEqual({ tool_id: ["filter1"] });
            expect(() => jobsFilterParams("filter", true)).toThrow(
                `${MAX_TOOL_NAME_MATCHES + 1} tools matched the provided name: filter. Please refine your search.`,
            );
        });

        it("combines a name filter with state, out of search", () => {
            const { params } = jobsFilterParams("cut state:ok", true);
            expect(params.state).toEqual(["ok"]);
            expect(params.tool_id?.sort()).toEqual(["adv_cut1", "cut1"]);
            expect(Object.keys(params).sort()).toEqual(["state", "tool_id"]);
        });

        it("does not set tool_id when no name text is present", () => {
            expect(jobsFilterParams("state:ok", true).params).toEqual({ state: ["ok"] });
        });

        it("matchesJob ignores the name/tool_id search here too", () => {
            const { matchesJob } = jobsFilterParams("cut", true);
            expect(matchesJob(buildJob({ tool_id: "unrelated" }))).toBe(true);
        });
    });

    describe("status text manipulation (JobStatusFilter's own usage)", () => {
        it("sets status on empty filter text", () => {
            const text = JobsFiltersById.applyFiltersToText({ status: "active" }, "");
            expect(text).toBe("status:active");
        });

        it("clears state when setting status", () => {
            let text = JobsFiltersById.applyFiltersToText({ state: "" }, "state:ok", true);
            text = JobsFiltersById.applyFiltersToText({ status: "problem" }, text);
            expect(jobsFilterParams(text).params).toEqual({ state: ["error", "failed"] });
        });

        it("clears status entirely when toggled off", () => {
            const text = JobsFiltersById.applyFiltersToText({ status: "" }, "status:active", true);
            expect(text).toBe("");
        });

        it("removing a key works even with no value at all for it", () => {
            // The whole point of the removal fix: a caller removing a filter has no real value to
            // give it, so an empty string (or any placeholder) must not block the removal.
            const text = JobsFiltersById.applyFiltersToText({ status: "" }, "status:active state:ok", true);
            expect(text).toBe("state:ok");
        });
    });
});
