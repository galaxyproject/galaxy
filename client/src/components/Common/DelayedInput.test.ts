import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { nextTick } from "vue";

import DelayedInput from "./DelayedInput.vue";

const localVue = getLocalVue();

function mountDelayedInput(props = {}) {
    return mount(DelayedInput as object, {
        localVue,
        propsData: {
            value: "test query",
            ...props,
        },
    });
}

describe("DelayedInput.vue", () => {
    it("refocuses the input after clearing the search", async () => {
        const wrapper = mountDelayedInput();
        const input = wrapper.find("input.g-form-input");
        const focusSpy = vi.spyOn(input.element as HTMLInputElement, "focus");

        await wrapper.find("button.search-clear").trigger("click");
        await nextTick();

        expect(focusSpy).toHaveBeenCalled();
    });
});
