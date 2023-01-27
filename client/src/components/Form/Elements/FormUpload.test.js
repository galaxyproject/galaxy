import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import FormUpload from "./FormUpload";

const localVue = getLocalVue();

describe("FormUpload", () => {
    const mountFormUpload = (props) =>
        mount(FormUpload, {
            propsData: props,
            localVue,
        });

    it("should display selected file in disabled textarea", async () => {
        const v = "H1, H2, H3\nv1, v2, v3";
        const wrapper = mountFormUpload({ value: v });
        const el = wrapper.find("textarea");
        expect(el.element.value).toEqual(v);
        expect(el.element.disabled).toBe(true);
    });

    it("should not display text box if file has not been selected", async () => {
        const wrapper = mountFormUpload({ value: null });
        const el = wrapper.find("textarea");
        expect(el.isVisible()).toBe(false);
        expect(el.text()).toBe("");
        const noInput = wrapper.find("label");
        expect(noInput.text()).toBe("No file chosen");
    });
});
