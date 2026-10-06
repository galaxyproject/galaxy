import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { mount, shallowMount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import type { WorkflowExtractionJob } from "@/api/histories";

import { toExtractionRow } from "./types";

import WorkflowExtractionCard from "./WorkflowExtractionCard.vue";
import GCard from "@/components/Common/GCard.vue";

const TOOL_OUTPUT = {
    id: "ds-1",
    hid: 1,
    name: "output1",
    history_content_type: "dataset",
    state: "ok",
    deleted: false,
    exposed: false,
    output_name: "out_file1",
} as NonNullable<WorkflowExtractionJob["outputs"]>[number];

const TOOL_JOB: WorkflowExtractionJob = {
    id: "job-tool-1",
    tool_id: "cat1",
    tool_name: "Concatenate",
    tool_version: "1.0",
    step_type: "tool",
    checked: true,
    seeded: false,
    tool_version_warning: null,
    outputs: [TOOL_OUTPUT],
};

const INPUT_JOB: WorkflowExtractionJob = {
    id: null,
    tool_id: null,
    tool_name: "Input Dataset",
    tool_version: null,
    step_type: "input_dataset",
    checked: true,
    seeded: false,
    tool_version_warning: null,
    outputs: [
        {
            id: "ds-2",
            hid: 2,
            name: "myfile.txt",
            history_content_type: "dataset",
            state: "ok",
            deleted: false,
            exposed: false,
        },
    ],
};

const localVue = getLocalVue();

describe("WorkflowExtractionCard seed_warning", () => {
    function cardBadges(job: WorkflowExtractionJob): Array<{ id: string; title?: string }> {
        const wrapper = shallowMount(WorkflowExtractionCard as object, {
            props: { job: toExtractionRow(job) },
            global: localVue,
        });
        return wrapper.getComponent(GCard).props("badges") ?? [];
    }

    it("renders a seed warning badge when seed_warning is set", () => {
        const badge = cardBadges({ ...INPUT_JOB, seed_warning: "Seeded as an input." }).find(
            (b) => b.id === "seed-warning",
        );
        expect(badge).toBeTruthy();
        expect(badge?.title).toBe("Seeded as an input.");
    });

    it("does not render a seed warning badge when seed_warning is absent", () => {
        expect(cardBadges(INPUT_JOB).find((b) => b.id === "seed-warning")).toBeFalsy();
    });
});

describe("WorkflowExtractionCard step label clear", () => {
    it("emits clear-step-label when GCard's clear-title button is clicked", async () => {
        const job = { ...toExtractionRow(TOOL_JOB), stepLabel: "concatenate" };
        const global = withPlugins(localVue, createTestingPinia({ createSpy: vi.fn }));
        const wrapper = mount(WorkflowExtractionCard as object, {
            props: { job },
            global: { ...global, stubs: { ...global.stubs, GenericHistoryItem: true } },
        });
        await wrapper.find(".g-card-clear-title").trigger("click");
        expect(wrapper.emitted("clear-step-label")).toHaveLength(1);
    });
});
