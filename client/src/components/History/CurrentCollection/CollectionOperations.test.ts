import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import CollectionOperations from "./CollectionOperations.vue";

vi.mock("vue-router", () => ({ useRoute: () => ({ fullPath: "/" }) }));

const localVue = getLocalVue();

function mountComponent(elementsStates: Record<string, number>, jobStateSummary: Record<string, number> = {}) {
    return mount(CollectionOperations as object, {
        props: {
            dsc: {
                id: "dsc_1",
                history_id: "hist_1",
                history_content_type: "dataset_collection",
                name: "reads",
                populated_state: "ok",
                visible: true,
                deleted: false,
                elements_states: elementsStates,
                job_state_summary: jobStateSummary,
            },
        },
        global: { ...localVue, stubs: { ...localVue.stubs, ExportToAnotherGalaxy: true } },
    });
}

describe("CollectionOperations", () => {
    it.each([
        ["every element is ok", true, { ok: 3 }, {}],
        ["an element is still running", false, { ok: 2, running: 1 }, {}],
        ["an element is queued", false, { ok: 2, queued: 1 }, {}],
        ["an element failed", false, { ok: 2, error: 1 }, {}],
        ["a job is still running", false, { ok: 3 }, { running: 1 }],
    ])("when %s, offers Export: %s", (_, offered, elementsStates, jobStateSummary) => {
        const wrapper = mountComponent(elementsStates, jobStateSummary);
        expect(wrapper.findComponent({ name: "ExportToAnotherGalaxy" }).exists()).toBe(offered);
    });
});
