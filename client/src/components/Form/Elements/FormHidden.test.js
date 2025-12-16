import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it } from "vitest";

import FormHidden from "./FormHidden.vue";

const localVue = getLocalVue();

describe("FormHidden", () => {
    let wrapper;

    beforeEach(() => {
        wrapper = mount(FormHidden, {
            props: {
                value: false,
                info: "info",
            },
            global: localVue,
        });
    });

    it("check initial value and value change", async () => {
        expect(wrapper.vm.value).toBe(false);
        await wrapper.setProps({ value: true });
        expect(wrapper.vm.value).toBe(true);
        expect(wrapper.text()).toBe("info");
    });
});
