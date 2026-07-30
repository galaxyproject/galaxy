import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { SubworkflowInfo } from "@/stores/workflowStepStore";

import NodeSubworkflow from "./NodeSubworkflow.vue";

const localVue = getLocalVue();

function subworkflowInfo(overrides: Partial<SubworkflowInfo> = {}): SubworkflowInfo {
    return {
        steps: [
            { order_index: 0, type: "data_input", label: "inner_input", name: "Input dataset" },
            { order_index: 1, type: "tool", label: "inner_tool", name: "cat1", tool_version: "1.0.0" },
        ],
        outdated_steps: [],
        shared_workflow_names: [],
        ...overrides,
    };
}

function mountPanel(info: SubworkflowInfo, expanded = true): Wrapper<Vue> {
    return mount(NodeSubworkflow as object, {
        propsData: { subworkflowInfo: info, expanded },
        localVue,
    });
}

describe("NodeSubworkflow", () => {
    it("summarizes the steps inside without listing them until expanded", () => {
        const collapsed = mountPanel(subworkflowInfo(), false);
        expect(collapsed.text()).toContain("2 steps");
        expect(collapsed.text()).not.toContain("inner_tool");

        const expanded = mountPanel(subworkflowInfo());
        expect(expanded.text()).toContain("inner_tool");
    });

    it("emits upgrade so the editor can act on it", async () => {
        const wrapper = mountPanel(
            subworkflowInfo({
                outdated_steps: [
                    {
                        order_index: 1,
                        name: "cat1",
                        type: "tool",
                        current_version: "1.0.0",
                        latest_version: "2.0.0",
                        subworkflow_path: [],
                    },
                ],
            }),
        );
        const upgrade = wrapper.findAll("button").filter((button) => button.text().includes("Upgrade"));
        expect(upgrade.length).toBe(1);
        await upgrade.at(0).trigger("click");
        expect(wrapper.emitted("upgrade")).toHaveLength(1);
    });

    it("emits edit so the editor can open the panel", async () => {
        const wrapper = mountPanel(subworkflowInfo());
        const edit = wrapper.findAll("button").filter((button) => button.text().includes("Edit"));
        expect(edit.length).toBe(1);
        await edit.at(0).trigger("click");
        expect(wrapper.emitted("edit")).toHaveLength(1);
    });

    it("only offers upgrade when something is out of date", () => {
        const wrapper = mountPanel(subworkflowInfo());
        expect(wrapper.findAll("button").filter((button) => button.text().includes("Upgrade")).length).toBe(0);
    });

    it("accounts for outdated steps further down rather than only counting them", () => {
        const wrapper = mountPanel(
            subworkflowInfo({
                outdated_steps: [
                    {
                        order_index: 0,
                        name: "nested_tool",
                        type: "tool",
                        current_version: "0.1",
                        latest_version: "0.2",
                        subworkflow_path: [1],
                    },
                ],
            }),
        );
        expect(wrapper.text()).toContain("1 outdated");
        expect(wrapper.text()).toContain("1 outdated further down");
    });

    it("says when editing here would change a workflow used elsewhere", () => {
        const wrapper = mountPanel(subworkflowInfo({ shared_workflow_names: ["Shared A", "Shared B"] }));
        expect(wrapper.text()).toContain("Shared A, Shared B");
    });
});
