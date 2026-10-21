import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import ClickToEdit from "./ClickToEdit.vue";

describe("ClickToEdit accessibility", () => {
    it.each(["enter", "space"])("starts editing with the %s key and saves the name", async (key) => {
        const wrapper = mount(ClickToEdit, {
            props: { value: "Dataset" },
            global: getLocalVue(),
            attachTo: document.body,
        });
        const trigger = wrapper.get("button");
        expect(trigger.attributes("type")).toBe("button");
        await trigger.trigger(`keydown.${key}`);
        const input = wrapper.get("input");
        expect(input.classes()).toContain("g-form-input");
        await vi.waitFor(() => expect(document.activeElement).toBe(input.element));
        await input.setValue("Renamed dataset");
        await input.trigger("keyup.enter");
        expect(wrapper.emitted("input")?.[0]).toEqual(["Renamed dataset"]);
        await wrapper.setProps({ value: "Renamed dataset" });
        expect(wrapper.get("button").text()).toBe("Renamed dataset");
        wrapper.unmount();
    });

    it("reverts the name with the escape key", async () => {
        const wrapper = mount(ClickToEdit, { props: { value: "Dataset" }, global: getLocalVue() });
        await wrapper.get("button").trigger("click");
        const input = wrapper.get("input");
        await input.setValue("Discarded");
        await input.trigger("keyup.escape");
        expect(wrapper.emitted("input")?.[0]).toEqual(["Dataset"]);
        expect(wrapper.find("input").exists()).toBe(false);
    });

    it("gives concurrently edited dataset inputs distinct ids", async () => {
        const wrapper = mount(
            {
                components: { ClickToEdit },
                template: '<div><ClickToEdit value="First" /><ClickToEdit value="Second" /></div>',
            },
            { global: getLocalVue() },
        );
        const triggers = wrapper.findAll("button");
        await triggers[0]!.trigger("click");
        await triggers[1]!.trigger("click");
        const inputs = wrapper.findAll("input");
        expect(inputs[0]!.attributes("id")).not.toBe(inputs[1]!.attributes("id"));
    });
});
