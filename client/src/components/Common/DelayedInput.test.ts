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
    it("clears search and refocuses without error", async () => {
        const wrapper = mountDelayedInput();

        await wrapper.find("button.search-clear").trigger("click");
        await nextTick();

        expect(wrapper.find("input.g-form-input").exists()).toBe(true);
        expect((wrapper.find("input.g-form-input").element as HTMLInputElement).value).toBe("");
    });
});
