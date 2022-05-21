import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import FormHidden from "./FormHidden";

const localVue = getLocalVue();

describe("FormHidden", () => {
    let wrapper;

    beforeEach(() => {
        wrapper = mount(FormHidden, {
            propsData: {
                value: false,
                info: "info",
            },
            localVue,
        });
    });

    it("check initial value and value change", async () => {
        expect(wrapper.vm.value).toBe(false);
        await wrapper.setProps({ value: true });
        expect(wrapper.vm.value).toBe(true);
        expect(wrapper.text()).toBe("info");
    });
});
