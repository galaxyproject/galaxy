import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import WorkflowStepIcon from "./WorkflowStepIcon.vue";

describe("WorkflowStepIcon", () => {
    it.each([
        // [stepType, iconName, rotated]
        ["tool", "wrench", false],
        ["data_input", "file", false],
        ["data_collection_input", "folder-open", false],
        ["subworkflow", "sitemap", true],
        ["parameter_input", "pencil-alt", false],
        ["pause", "pause", false],
        ["pick_value", "code-branch", false],
    ] as const)("draws the %s icon", (stepType, iconName, rotated) => {
        const wrapper = mount(WorkflowStepIcon, { props: { stepType } });

        const icon = wrapper.find("svg");
        expect(icon.attributes("data-icon")).toBe(iconName);
        expect(icon.classes("fa-rotate-270")).toBe(rotated);
    });
});
