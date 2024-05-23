import { getLocalVue } from "@tests/jest/helpers";
import { mount, Wrapper } from "@vue/test-utils";

import FormHidden from "./FormHidden.vue";

const localVue = getLocalVue();

describe("FormHidden", () => {
    let wrapper: Wrapper<Vue>;

    beforeEach(() => {
        wrapper = mount(FormHidden as object, {
            propsData: {
                info: "info",
            },
            localVue,
        });
    });

    it("check initial value and value change", async () => {
        expect(wrapper.text()).toBe("info");
    });
});
