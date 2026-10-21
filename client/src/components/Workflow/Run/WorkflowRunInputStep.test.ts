import { getFakeDatasetSummary } from "@tests/test-data/datasets";
import { getLocalVue, nth } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { h, nextTick } from "vue";

import type { FormInputNode } from "@/components/Form/composables/useFormState";
import { DEFAULT_OPTIONS_PAGE_SIZE } from "@/components/Form/Elements/FormData/types";

import { searchHistoryContents } from "./services";

import WorkflowRunInputStep from "./WorkflowRunInputStep.vue";
import FormCard from "@/components/Form/FormCard.vue";

vi.mock("./services", () => ({
    searchHistoryContents: vi.fn(async () => []),
}));

vi.mock("@/components/Form/FormDisplay.vue", () => ({
    default: {
        name: "FormDisplay",
        props: ["inputs", "validationScrollTo"],
        render: () => h("div"),
    },
}));

const globalConfig = getLocalVue();

interface InputStepModel {
    index: string;
    step_type: "parameter_input" | "data_input";
    step_label: string;
    fixed_title: string;
    expanded: boolean;
    inputs: FormInputNode[];
}

function mountStep(stepOverrides: Partial<InputStepModel> = {}) {
    const model: InputStepModel = {
        index: "1",
        step_type: "parameter_input",
        step_label: "my_param",
        fixed_title: "2: my_param",
        expanded: false,
        inputs: [{ name: "input", type: "text", value: "" }],
        ...stepOverrides,
    };
    return mount(WorkflowRunInputStep, {
        props: {
            model,
            validationScrollTo: [],
            historyId: "history_id",
        },
        global: globalConfig,
    });
}

describe("WorkflowRunInputStep", () => {
    beforeEach(() => {
        vi.useFakeTimers();
        vi.mocked(searchHistoryContents).mockReset();
        vi.mocked(searchHistoryContents).mockResolvedValue([]);
    });

    afterEach(() => {
        vi.clearAllTimers();
        vi.useRealTimers();
    });
    // Vitest runs afterEach hooks in reverse order; cancel debounces before restoring the clock.
    enableAutoUnmount(afterEach);

    it("renders local copies of the step inputs", () => {
        const wrapper = mountStep({ step_type: "data_input" });
        const inputs = wrapper.getComponent({ name: "FormDisplay" }).props("inputs");
        expect(inputs).toEqual([{ name: "input", type: "text", value: "", flavor: "module", hide_label: true }]);
        expect(wrapper.find("[step-label='my_param']").exists()).toBe(true);
    });

    it("rebuilds the local inputs when the step inputs are replaced", async () => {
        const wrapper = mountStep();
        const model = wrapper.props("model");
        await wrapper.setProps({ model: { ...model, inputs: [{ name: "other", type: "integer", value: 1 }] } });
        expect(wrapper.getComponent({ name: "FormDisplay" }).props("inputs")).toEqual([
            { name: "other", type: "integer", value: 1, flavor: "module", hide_label: false },
        ]);
    });

    it("shows a placeholder when the step has no inputs", () => {
        const wrapper = mountStep({ inputs: [] });
        expect(wrapper.findComponent({ name: "FormDisplay" }).exists()).toBe(false);
        expect(wrapper.text()).toContain("No options available.");
    });

    it("forwards form events with the step index", async () => {
        const wrapper = mountStep();
        const form = wrapper.getComponent({ name: "FormDisplay" });
        form.vm.$emit("onChange", { input: "value" });
        form.vm.$emit("onValidation", ["input", "Required"]);
        await nextTick();
        expect(wrapper.emitted("onChange")).toEqual([["1", { input: "value" }]]);
        expect(wrapper.emitted("onValidation")).toEqual([["1", ["input", "Required"]]]);
    });

    it("toggles the card through its expanded event", async () => {
        const wrapper = mountStep();
        const card = wrapper.getComponent(FormCard);
        expect(card.props("expanded")).toBe(false);
        card.vm.$emit("update:expanded", true);
        await nextTick();
        expect(card.props("expanded")).toBe(true);
    });

    it("expands and scrolls to the input named by a validation error", async () => {
        const wrapper = mountStep();
        const form = wrapper.getComponent({ name: "FormDisplay" });
        expect(form.props("validationScrollTo")).toBeNull();
        await wrapper.setProps({ validationScrollTo: ["input", "Required"] });
        expect(wrapper.getComponent(FormCard).props("expanded")).toBe(true);
        expect(form.props("validationScrollTo")).toEqual(["input", "Required"]);
    });

    it("merges fetched options into the input", async () => {
        vi.mocked(searchHistoryContents).mockResolvedValueOnce([
            getFakeDatasetSummary({ id: "d1", name: "one", hid: 1, tags: [] }),
        ]);
        const wrapper = mountStep();
        const form = wrapper.getComponent({ name: "FormDisplay" });
        form.vm.$emit("load-more", { name: "input", src: "hda", offset: 0, limit: 1 });
        await flushPromises();
        expect(searchHistoryContents).toHaveBeenCalledWith(
            "history_id",
            expect.objectContaining({ type: "dataset", offset: 0, limit: 1 }),
        );
        const input = nth<FormInputNode>(form.props("inputs"), 0);
        expect(input.options).toEqual({
            hda: [{ id: "d1", src: "hda", name: "one", hid: 1, keep: false, tags: [] }],
        });
        expect(input.options_meta).toEqual({ hda: { offset: 0, limit: 1, has_more: true } });
    });

    it("debounces option searches", async () => {
        const wrapper = mountStep();
        const form = wrapper.getComponent({ name: "FormDisplay" });
        form.vm.$emit("search-change", { name: "input", src: "hda", query: "a" });
        form.vm.$emit("search-change", { name: "input", src: "hda", query: "ab" });
        expect(searchHistoryContents).not.toHaveBeenCalled();
        vi.advanceTimersByTime(400);
        expect(searchHistoryContents).toHaveBeenCalledTimes(1);
        expect(searchHistoryContents).toHaveBeenCalledWith(
            "history_id",
            expect.objectContaining({ search: "ab", offset: 0, limit: DEFAULT_OPTIONS_PAGE_SIZE }),
        );
        await flushPromises();
    });

    it("cancels a pending search when unmounted", () => {
        const wrapper = mountStep();
        wrapper.getComponent({ name: "FormDisplay" }).vm.$emit("search-change", {
            name: "input",
            src: "hda",
            query: "a",
        });
        wrapper.unmount();
        vi.advanceTimersByTime(400);
        expect(searchHistoryContents).not.toHaveBeenCalled();
    });
});
