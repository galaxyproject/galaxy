import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import FormUpload from "./FormUpload.vue";

const localVue = getLocalVue();

describe("FormUpload", () => {
    enableAutoUnmount(afterEach);

    const mountFormUpload = (props) =>
        mount(FormUpload, {
            props,
            global: localVue,
        });

    it("should display selected file in disabled textarea", () => {
        const fileContent = "H1, H2, H3\nv1, v2, v3";
        const wrapper = mountFormUpload({ value: fileContent });
        const textarea = wrapper.get("textarea");
        expect(textarea.element.value).toEqual(fileContent);
        expect(textarea.element.disabled).toBe(true);
    });

    it("should not display text box if file has not been selected", () => {
        const wrapper = mountFormUpload({ value: null });
        const textarea = wrapper.get("textarea");
        // happy-dom's getComputedStyle doesn't reflect inline styles reliably, so
        // isVisible() (which relies on it) can't be used here -- check the v-show
        // style directly instead.
        expect(textarea.element.style.display).toBe("none");
        expect(textarea.text()).toBe("");
        const noInput = wrapper.get("label");
        expect(noInput.text()).toBe("No file chosen");
    });
});
