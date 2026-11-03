import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import FormHidden from "./FormHidden.vue";

const localVue = getLocalVue();
enableAutoUnmount(afterEach);

describe("FormHidden", () => {
    it("retains the hidden value when it changes and displays the supplied info", async () => {
        const wrapper = mount(FormHidden, {
            props: {
                value: false,
                info: "info",
            },
            global: localVue,
        });

        expect(wrapper.vm.value).toBe(false);
        await wrapper.setProps({ value: true });
        expect(wrapper.vm.value).toBe(true);
        expect(wrapper.text()).toBe("info");
    });
});
