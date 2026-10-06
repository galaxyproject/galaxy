import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { h } from "vue";

import { useHistoryItemsStore } from "@/stores/historyItemsStore";

import { getTool } from "./services";

import WorkflowRunDefaultStep from "./WorkflowRunDefaultStep.vue";
import FormCard from "@/components/Form/FormCard.vue";

vi.mock("./services", () => ({
    getTool: vi.fn(),
}));

vi.mock("@/components/Form/FormDisplay.vue", () => ({
    default: {
        name: "FormDisplay",
        props: ["inputs", "replaceParams", "validationScrollTo"],
        render: () => h("div"),
    },
}));

vi.mock("@/components/Tool/ToolCredentials.vue", () => ({
    default: {
        name: "ToolCredentials",
        props: ["toolId", "toolVersion"],
        render: () => h("div"),
    },
}));

const globalConfig = getLocalVue();

function toolModel(options: unknown[]) {
    return { inputs: [{ name: "input", type: "data", options: { hda: options } }] };
}

function mountStep(stepOverrides: Record<string, unknown> = {}) {
    const pinia = createTestingPinia({ createSpy: vi.fn });
    setActivePinia(pinia);
    return mount(WorkflowRunDefaultStep, {
        props: {
            model: {
                index: "2",
                id: "cat1",
                version: "1.0",
                step_type: "tool",
                step_label: "concat",
                fixed_title: "3: Concatenate",
                expanded: false,
                inputs: [{ name: "input", type: "data", options: { hda: [{ id: "d1", src: "hda" }] } }],
                ...stepOverrides,
            },
            replaceParams: { input: "linked" },
            validationScrollTo: [],
            historyId: "history_id",
        },
        global: {
            ...globalConfig,
            plugins: [...(globalConfig.plugins ?? []), pinia],
        },
    });
}

describe("WorkflowRunDefaultStep", () => {
    beforeEach(() => {
        vi.useFakeTimers();
        vi.mocked(getTool).mockReset();
        vi.mocked(getTool).mockResolvedValue(toolModel([{ id: "d2", src: "hda" }]));
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it("passes the step inputs and replacement parameters to the form", () => {
        const wrapper = mountStep();
        const form = wrapper.findComponent({ name: "FormDisplay" });
        expect(form.props("inputs")).toEqual([
            { name: "input", type: "data", options: { hda: [{ id: "d1", src: "hda" }] } },
        ]);
        expect(form.props("replaceParams")).toEqual({ input: "linked" });
        expect(wrapper.findComponent({ name: "ToolCredentials" }).exists()).toBe(false);
    });

    it("shows credentials for tools that need them", () => {
        const wrapper = mountStep({ credentials: [{ name: "service" }] });
        const credentials = wrapper.findComponent({ name: "ToolCredentials" });
        expect(credentials.props()).toEqual({ toolId: "cat1", toolVersion: "1.0" });
    });

    it("forwards form events with the step index", async () => {
        const wrapper = mountStep();
        const form = wrapper.findComponent({ name: "FormDisplay" });
        form.vm.$emit("onChange", { input: "value" });
        form.vm.$emit("onValidation", ["input", "Required"]);
        await wrapper.vm.$nextTick();
        expect(wrapper.emitted("onChange")).toEqual([["2", { input: "value" }]]);
        expect(wrapper.emitted("onValidation")).toEqual([["2", ["input", "Required"]]]);
        expect(getTool).not.toHaveBeenCalled();
    });

    it("rebuilds the tool form when a change requests a refresh", async () => {
        const wrapper = mountStep();
        const form = wrapper.findComponent({ name: "FormDisplay" });
        const before = form.props("inputs");
        form.vm.$emit("onChange", { input: "value" }, true);
        await flushPromises();
        expect(getTool).toHaveBeenCalledWith("cat1", "1.0", { input: "value" }, "history_id");
        expect(form.props("inputs")).not.toBe(before);
        expect(form.props("inputs")[0].options).toEqual({ hda: [{ id: "d2", src: "hda" }] });
    });

    it("refreshes the tool form when the history changes", async () => {
        const wrapper = mountStep();
        useHistoryItemsStore().lastUpdateTime = new Date(0);
        await flushPromises();
        expect(getTool).toHaveBeenCalledTimes(1);
        expect(wrapper.emitted("onChange")).toBeUndefined();
    });

    it("shows the error when the tool form cannot be built", async () => {
        vi.mocked(getTool).mockRejectedValue("Tool not found");
        const wrapper = mountStep();
        wrapper.findComponent({ name: "FormDisplay" }).vm.$emit("onChange", {}, true);
        await flushPromises();
        expect(wrapper.text()).toContain("Tool not found");
    });

    it("toggles the card and expands on validation errors", async () => {
        const wrapper = mountStep();
        const card = wrapper.findComponent(FormCard);
        const form = wrapper.findComponent({ name: "FormDisplay" });
        expect(card.props("expanded")).toBe(false);
        expect(form.props("validationScrollTo")).toBeNull();
        card.vm.$emit("update:expanded", true);
        await wrapper.vm.$nextTick();
        expect(card.props("expanded")).toBe(true);
        card.vm.$emit("update:expanded", false);
        await wrapper.setProps({ validationScrollTo: ["input", "Required"] });
        expect(card.props("expanded")).toBe(true);
        expect(form.props("validationScrollTo")).toEqual(["input", "Required"]);
    });

    it("appends paged options to the input", async () => {
        const wrapper = mountStep();
        const form = wrapper.findComponent({ name: "FormDisplay" });
        form.vm.$emit("load-more", { name: "input", src: "hda", offset: 1, limit: 1 });
        await flushPromises();
        expect(getTool).toHaveBeenCalledWith("cat1", "1.0", {}, "history_id", {
            input: { hda: { offset: 1, limit: 1 } },
        });
        expect(form.props("inputs")[0].options.hda).toEqual([
            { id: "d1", src: "hda" },
            { id: "d2", src: "hda" },
        ]);
    });

    it("debounces option searches and cancels them when unmounted", async () => {
        const wrapper = mountStep();
        const form = wrapper.findComponent({ name: "FormDisplay" });
        form.vm.$emit("search-change", { name: "input", src: "hda", query: "a", limit: 10 });
        form.vm.$emit("search-change", { name: "input", src: "hda", query: "ab", limit: 10 });
        vi.advanceTimersByTime(400);
        expect(getTool).toHaveBeenCalledTimes(1);
        expect(getTool).toHaveBeenCalledWith("cat1", "1.0", {}, "history_id", {
            input: { hda: { offset: 0, limit: 10, search: "ab" } },
        });
        form.vm.$emit("search-change", { name: "input", src: "hda", query: "abc", limit: 10 });
        wrapper.unmount();
        vi.advanceTimersByTime(400);
        expect(getTool).toHaveBeenCalledTimes(1);
    });
});
