import { shallowMount } from "@vue/test-utils";

import MarkdownVisualization from "./MarkdownVisualization";

describe("Markdown/MarkdownVisualization", () => {
    it("test wizard", async () => {
        const wrapper = shallowMount(MarkdownVisualization, {
            propsData: {
                argumentName: "name",
                argumentPayload: {
                    settings: [{}, {}],
                    tracks: [{}],
                },
                history: "history_id",
                labels: [],
                useLabels: false,
            },
        });
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.labelShow).toBe(false);
        expect(Object.keys(wrapper.vm.formInputs).length).toBe(3);
        wrapper.vm.onData("history_dataset_id");
        expect(wrapper.vm.dataShow).toBe(false);
        expect(wrapper.vm.dataTag).toBe("history_dataset_id=history_dataset_id");
        expect(wrapper.vm.formShow).toBe(true);
    });

    it("test wizard", async () => {
        const wrapper = shallowMount(MarkdownVisualization, {
            propsData: {
                argumentName: "name",
                argumentPayload: {},
                history: "history_id",
                labels: [],
                useLabels: true,
            },
        });
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.labelShow).toBe(true);
        expect(wrapper.vm.formInputs).toBe(null);
    });
});
