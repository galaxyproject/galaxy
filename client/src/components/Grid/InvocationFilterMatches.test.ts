import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { AnyHistoryEntry } from "@/api/histories";
import type { WorkflowSummary } from "@/api/workflows";

import type { InvocationFilterMatches } from "./configs/invocationFilters";

import MountTarget from "./InvocationFilterMatches.vue";

const localVue = getLocalVue();

function mountMatches(matches?: InvocationFilterMatches) {
    return mount(MountTarget as object, {
        global: {
            ...localVue,
            stubs: {
                WorkflowCardList: {
                    name: "WorkflowCardList",
                    props: ["workflows"],
                    template: "<ul class='workflow-cards' />",
                },
                HistoryCardList: {
                    name: "HistoryCardList",
                    props: ["histories"],
                    template: "<ul class='history-cards' />",
                },
            },
        },
        props: { matches },
    });
}

const workflows = [{ id: "workflow-1" }, { id: "workflow-2" }] as WorkflowSummary[];
const histories = [{ id: "history-1" }] as AnyHistoryEntry[];

describe("InvocationFilterMatches", () => {
    it("renders nothing without name matches", () => {
        expect(mountMatches({}).text()).toBe("");
    });

    it("lists the matching workflows and histories", async () => {
        const wrapper = mountMatches({
            workflows: { search: "rna", items: workflows, truncated: false },
            histories: { search: "'My data'", items: histories, truncated: true },
        });

        const workflowSection = wrapper.find("[data-description='invocation filter workflow matches']");
        expect(workflowSection.text()).toContain('2 workflows match "rna"');
        expect(workflowSection.findComponent({ name: "WorkflowCardList" }).props("workflows")).toEqual(workflows);

        const historySection = wrapper.find("[data-description='invocation filter history matches']");
        expect(historySection.text()).toContain('1 history matches "My data"');
        expect(historySection.text()).toContain("More histories match");
        expect(historySection.findComponent({ name: "HistoryCardList" }).props("histories")).toEqual(histories);

        await workflowSection.find("button").trigger("click");
        expect(workflowSection.find(".workflow-cards").exists()).toBe(false);
    });

    it("says when a name matches nothing", () => {
        const wrapper = mountMatches({ workflows: { search: "missing", items: [], truncated: false } });

        expect(wrapper.text()).toContain('No workflows match "missing"');
        expect(wrapper.find(".workflow-cards").exists()).toBe(false);
    });
});
