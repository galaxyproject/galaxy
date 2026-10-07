import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import WorkflowStepIcon from "./WorkflowStepIcon.vue";

describe("WorkflowStepIcon", () => {
    it.each([
        ["tool", "wrench"],
        ["data_input", "file"],
        ["data_collection_input", "folder-open"],
        ["subworkflow", "sitemap"],
        ["parameter_input", "pencil-alt"],
        ["pause", "pause"],
        ["pick_value", "code-branch"],
    ])("draws the %s icon", (stepType, iconName) => {
        const wrapper = mount(WorkflowStepIcon as object, { propsData: { stepType } });

        expect(wrapper.find("svg").attributes("data-icon")).toBe(iconName);
    });
});
