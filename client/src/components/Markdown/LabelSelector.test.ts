import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { WorkflowLabel } from "./Editor/types";

import LabelSelector from "./LabelSelector.vue";

const localVue = getLocalVue();

const LABELS: WorkflowLabel[] = [
    { label: "input_a", type: "input" },
    { label: "output_b", type: "output" },
];

function mountSelector(value?: WorkflowLabel, labels = LABELS) {
    return mount(LabelSelector as object, {
        props: { hasLabels: labels.length > 0, labels, labelTitle: "Input", value },
        global: localVue,
    });
}

function radios(wrapper: ReturnType<typeof mountSelector>) {
    return wrapper.findAll<HTMLInputElement>("input[type=radio]");
}

describe("LabelSelector", () => {
    it("names the radio group by its heading", () => {
        const wrapper = mountSelector();
        const group = wrapper.find("[role=radiogroup]");
        const heading = wrapper.find("h2");
        expect(heading.text()).toBe("Select Input Label:");
        expect(group.attributes("aria-labelledby")).toBe(heading.attributes("id"));
        expect(radios(wrapper).map((radio) => radio.element.labels?.[0]?.textContent?.trim())).toEqual([
            "input_a",
            "output_b",
        ]);
    });

    it("emits the chosen label", async () => {
        const wrapper = mountSelector();
        await radios(wrapper)[1]!.setValue(true);
        expect(wrapper.emitted("input")?.[0]).toEqual([LABELS[1]]);
    });

    it("checks the radio of the current value", () => {
        const wrapper = mountSelector(LABELS[1]);
        expect(radios(wrapper).map((radio) => radio.element.checked)).toEqual([false, true]);
    });

    it("explains how to add labels when there are none", () => {
        const wrapper = mountSelector(undefined, []);
        expect(wrapper.find("[role=radiogroup]").exists()).toBe(false);
        expect(wrapper.text()).toContain("No labels found.");
    });
});
