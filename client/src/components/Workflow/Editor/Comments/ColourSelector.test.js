import { mount } from "@vue/test-utils";
import { nextTick } from "vue";

import { colours } from "./colours";

import ColourSelector from "./ColourSelector.vue";

describe("ColourSelector", () => {
    it("shows a button for each colour and 'none'", () => {
        const wrapper = mount(ColourSelector, { propsData: { colour: "none" } });
        const buttons = wrapper.findAll("button");
        expect(buttons.length).toBe(Object.keys(colours).length + 1);
    });

    it("highlights the selected colour", async () => {
        const wrapper = mount(ColourSelector, { propsData: { colour: "none" } });
        const allSelected = wrapper.findAll(".selected");
        expect(allSelected.length).toBe(1);

        let selected = allSelected.wrappers[0];
        expect(selected.element.getAttribute("title")).toBe("No Colour");

        const colourNames = Object.keys(colours);

        for (let i = 0; i < colourNames.length; i++) {
            const colour = colourNames[i];
            wrapper.setProps({ colour });
            await nextTick();

            selected = wrapper.find(".selected");

            expect(selected.element.getAttribute("title")).toContain(colour);
        }
    });

    it("emits the set colour", async () => {
        const wrapper = mount(ColourSelector, { propsData: { colour: "none" } });

        const colourNames = Object.keys(colours);

        for (let i = 0; i < colourNames.length; i++) {
            const colour = colourNames[i];
            await wrapper.find(`[title="Colour ${colour}"]`).trigger("click");
            expect(wrapper.emitted()["set-colour"][i][0]).toBe(colour);
        }
    });
});
