import { emittedArg, getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import FormInput from "./FormInput.vue";

enableAutoUnmount(afterEach);

function mountFormInput() {
    return mount(FormInput, {
        props: {
            id: "input",
            value: "initial_value",
        },
        global: getLocalVue(),
    });
}

describe("FormInput", () => {
    it("shows its value in a text input and emits the edit", async () => {
        const wrapper = mountFormInput();
        const input = wrapper.find("input");
        expect(input.element.value).toBe("initial_value");

        await input.setValue("new_value");

        expect(input.element.value).toBe("new_value");
        expect(emittedArg(wrapper, "input")).toBe("new_value");
    });

    it("switches to a textarea that keeps the value and emits the edit", async () => {
        const wrapper = mountFormInput();

        await wrapper.setProps({ area: true });

        expect(wrapper.find("input").exists()).toBe(false);
        const textarea = wrapper.find("textarea");
        expect(textarea.element.value).toBe("initial_value");

        await textarea.setValue("new_value");

        expect(textarea.element.value).toBe("new_value");
        expect(emittedArg(wrapper, "input")).toBe("new_value");
    });
});
