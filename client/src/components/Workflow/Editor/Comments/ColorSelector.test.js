import { mount } from "@vue/test-utils";
import { nextTick } from "vue";

import { colors } from "./colors";

import ColorSelector from "./ColorSelector.vue";

describe("ColorSelector", () => {
    it("shows a button for each color and 'none'", () => {
        const wrapper = mount(ColorSelector, { propsData: { color: "none" } });
        const buttons = wrapper.findAll("button");
        expect(buttons.length).toBe(Object.keys(colors).length + 1);
    });

    it("highlights the selected color", async () => {
        const wrapper = mount(ColorSelector, { propsData: { color: "none" } });
        const allSelected = wrapper.findAll(".selected");
        expect(allSelected.length).toBe(1);

        let selected = allSelected.wrappers[0];
        expect(selected.element.getAttribute("title")).toBe("No Color");

        const colorNames = Object.keys(colors);

        for (let i = 0; i < colorNames.length; i++) {
            const color = colorNames[i];
            wrapper.setProps({ color });
            await nextTick();

            selected = wrapper.find(".selected");

            expect(selected.element.getAttribute("title")).toContain(color);
        }
    });

    it("emits the set color", async () => {
        const wrapper = mount(ColorSelector, { propsData: { color: "none" } });

        const colorNames = Object.keys(colors);

        for (let i = 0; i < colorNames.length; i++) {
            const color = colorNames[i];
            await wrapper.find(`[title="Color ${color}"]`).trigger("click");
            expect(wrapper.emitted()["set-color"][i][0]).toBe(color);
        }
    });
});
