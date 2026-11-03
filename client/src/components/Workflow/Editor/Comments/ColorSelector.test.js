import { emittedArg } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import { colors } from "./colors";

import ColorSelector from "./ColorSelector.vue";

describe("ColorSelector", () => {
    enableAutoUnmount(afterEach);
    it("shows a button for each color and 'none'", () => {
        const wrapper = mount(ColorSelector, { props: { color: "none" } });
        const buttons = wrapper.findAll("button");
        expect(buttons.length).toBe(Object.keys(colors).length + 1);
    });

    it("highlights the selected color", async () => {
        const wrapper = mount(ColorSelector, { props: { color: "none" } });
        const allSelected = wrapper.findAll(".selected");
        expect(allSelected.length).toBe(1);

        expect(wrapper.get(".selected").attributes("title")).toBe("No Color");

        const colorNames = Object.keys(colors);

        for (const color of colorNames) {
            await wrapper.setProps({ color });

            expect(wrapper.get(".selected").attributes("title")).toContain(color);
        }
    });

    it("emits the set color", async () => {
        const wrapper = mount(ColorSelector, { props: { color: "none" } });

        const colorNames = Object.keys(colors);

        for (const [index, color] of colorNames.entries()) {
            await wrapper.get(`[title="Color ${color}"]`).trigger("click");
            expect(emittedArg(wrapper, "set-color", index)).toBe(color);
        }
    });
});
