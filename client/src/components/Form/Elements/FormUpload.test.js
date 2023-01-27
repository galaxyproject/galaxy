import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import FormUpload from "./FormUpload";

const localVue = getLocalVue();

describe("FormUpload", () => {
    const mountFormUpload = async (props) =>
        await mount(FormUpload, {
            propsData: props,
            localVue,
        });

    it("should display selected file in disabled textarea", async () => {
        const v = "H1, H2, H3\nv1, v2, v3";
        const wrapper = await mountFormUpload({ value: v });
        const el = wrapper.find("textarea");
        expect(el.element.value).toEqual(v);
        const isDisabled = el.element.disabled === true;
        expect(isDisabled).toBe(true);
    });

    it("should not display text box if file has not been selected", async () => {
        const v = "";
        const wrapper = await mountFormUpload({ value: v });
        const el = wrapper.find("textarea");
        expect(el.isVisible()).toBe(false);
    });
});
