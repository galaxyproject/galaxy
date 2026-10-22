import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import FormColor from "./FormColor.vue";

describe("FormColor", () => {
    it("renders a small color GFormInput and emits the picked color", async () => {
        const wrapper = mount(FormColor, { props: { id: "color-field", value: "#000000" }, global: getLocalVue() });
        const input = wrapper.get("input#color-field");
        expect(input.attributes("type")).toBe("color");
        expect(input.classes()).toEqual(expect.arrayContaining(["g-form-input", "g-small"]));
        expect(wrapper.get("label").attributes("for")).toBe("color-field");

        await input.setValue("#ff0000");
        expect(wrapper.emitted("input")?.at(-1)).toEqual(["#ff0000"]);
    });
});
