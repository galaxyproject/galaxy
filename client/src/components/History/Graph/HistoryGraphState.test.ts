import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import HistoryGraphState from "./HistoryGraphState.vue";

const localVue = getLocalVue();

function mountState(props: Record<string, unknown>) {
    return mount(HistoryGraphState as object, {
        props: { loading: false, nodeCount: 3, executionCount: 1, ...props },
        slots: { default: "<div class='graph'>graph</div>" },
        global: localVue,
    });
}

describe("HistoryGraphState", () => {
    it("shows the error before anything else", () => {
        const wrapper = mountState({ error: "Not accessible", loading: true });
        expect(wrapper.text()).toContain("Not accessible");
        expect(wrapper.find(".graph").exists()).toBe(false);
    });

    it("shows loading", () => {
        const wrapper = mountState({ loading: true });
        expect(wrapper.text()).toContain("Loading history graph");
        expect(wrapper.find(".graph").exists()).toBe(false);
    });

    it("shows the default empty message", () => {
        expect(mountState({ nodeCount: 0 }).text()).toContain("This history is empty.");
    });

    it("shows a custom empty message", () => {
        expect(mountState({ nodeCount: 0, emptyMessage: "Add datasets." }).text()).toContain("Add datasets.");
    });

    it("explains a history without tool executions", () => {
        const wrapper = mountState({ executionCount: 0 });
        expect(wrapper.text()).toContain("No History Graph available.");
        expect(wrapper.find(".graph").exists()).toBe(false);
    });

    it("shows the graph otherwise", () => {
        expect(mountState({}).find(".graph").exists()).toBe(true);
    });
});
