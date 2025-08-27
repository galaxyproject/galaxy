import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import FormHidden from "./FormHidden";

const globalConfig = getLocalVue();

describe("FormHidden", () => {
    let wrapper;

    beforeEach(() => {
        wrapper = mount(FormHidden, {
            props: {
                value: false,
                info: "info",
            },
            global: globalConfig.global,
        });
    });

    it("check initial value and value change", async () => {
        expect(wrapper.vm.value).toBe(false);
        await wrapper.setProps({ value: true });
        expect(wrapper.vm.value).toBe(true);
        expect(wrapper.text()).toBe("info");
    });
});
