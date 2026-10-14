import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import { defineComponent } from "vue";

import GForm from "./GForm.vue";

describe("GForm", () => {
    it("hands the native submit event to a parent's @submit.prevent handler", async () => {
        const onSubmit = vi.fn();
        const Host = defineComponent({
            components: { GForm },
            setup: () => ({ onSubmit }),
            template: `<GForm @submit.prevent="onSubmit"><input name="name" /></GForm>`,
        });
        const wrapper = mount(Host);

        const event = new Event("submit", { cancelable: true });
        wrapper.find("form").element.dispatchEvent(event);

        expect(onSubmit).toHaveBeenCalledTimes(1);
        // Without preventDefault the browser does a real form submit and reloads the page.
        expect(event.defaultPrevented).toBe(true);
    });

    it("prevents the page reload with a bare @submit.prevent", async () => {
        const Host = defineComponent({
            components: { GForm },
            template: `<GForm @submit.prevent><input name="name" /></GForm>`,
        });
        const wrapper = mount(Host);

        const event = new Event("submit", { cancelable: true });
        wrapper.find("form").element.dispatchEvent(event);

        expect(event.defaultPrevented).toBe(true);
    });
});
