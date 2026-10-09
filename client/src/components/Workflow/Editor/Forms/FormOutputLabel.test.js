import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, describe, expect, it } from "vitest";

import { useWorkflowStepStore } from "@/stores/workflowStepStore";

import FormOutputLabel from "./FormOutputLabel.vue";

enableAutoUnmount(afterEach);

describe("FormOutputLabel", () => {
    function mountOutputLabels() {
        const outputs = [
            { name: "output-name", label: "output-label" },
            { name: "other-name", label: "other-label" },
        ];
        const global = getLocalVue();
        const pinia = createPinia();
        setActivePinia(pinia);
        const stepStore = useWorkflowStepStore("mock-workflow");

        function mountLabel(id, name) {
            const step = { id, outputs: [{ name }], workflow_outputs: outputs.map((output) => ({ ...output })) };
            const wrapper = mount(FormOutputLabel, {
                props: { name, step },
                global: { ...withPlugins(global, pinia), provide: { workflowId: "mock-workflow" } },
            });
            stepStore.addStep(step);
            return wrapper;
        }

        return { wrapper: mountLabel(0, "output-name"), wrapperOther: mountLabel(1, "other-name"), stepStore };
    }

    it("shows output-specific details when requested", async () => {
        const { wrapper } = mountOutputLabels();
        const title = wrapper.find(".ui-form-title-text");
        expect(title.text()).toBe("Label");
        await wrapper.setProps({ showDetails: true });
        expect(title.text()).toBe("Label for: 'output-name'");
    });

    it("rejects another step’s label while preserving both accepted labels", async () => {
        const { wrapper, wrapperOther, stepStore } = mountOutputLabels();
        const input = wrapper.find("input");
        const inputOther = wrapperOther.find("input");
        await input.setValue("new-label");
        expect(wrapper.find(".ui-form-error").exists()).toBe(false);
        expect(wrapperOther.find(".ui-form-error").exists()).toBe(false);
        await inputOther.setValue("other-label");
        expect(wrapper.find(".ui-form-error").exists()).toBe(false);
        expect(wrapperOther.find(".ui-form-error").exists()).toBe(false);
        await input.setValue("other-label");
        expect(wrapper.find(".ui-form-error").text()).toBe("Duplicate output label 'other-label' will be ignored.");
        expect(wrapperOther.find(".ui-form-error").exists()).toBe(false);
        expect(stepStore.workflowOutputs["new-label"].outputName).toBe("output-name");
    });
});
