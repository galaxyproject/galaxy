import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import FormText from "./FormText";

const globalConfig = getLocalVue();

describe("FormText", () => {
    const mountFormText = async (props) =>
        await mount(FormText, {
            props,
            global: globalConfig.global,
        });

    it("should render the appropriate input type", async () => {
        const wrapper = await mountFormText({});
        const el = wrapper.find("input");
        expect(el.exists()).toBe(true);
        expect(el.attributes("type")).toBe("text");
        
        await wrapper.setProps({ type: "password" });
        const elPassword = wrapper.find("input");
        expect(elPassword.exists()).toBe(true);
        expect(elPassword.attributes("type")).toBe("password");
        
        await wrapper.setProps({ type: "anyothertype" });
        const elOtherType = wrapper.find("input");
        expect(elOtherType.exists()).toBe(true);
        expect(elOtherType.attributes("type")).toBe("text");
    });

    it("should render the appropriate component", async () => {
        const wrapper = await mountFormText({ area: true });
        // b-form-textarea doesn't render as <textarea> in Vue 3 compat mode
        const el = wrapper.find("b-form-textarea");
        expect(el.exists()).toBe(true);
        await wrapper.setProps({ area: false, multiple: true });
        const elMultiple = wrapper.find("b-form-textarea");
        expect(elMultiple.exists()).toBe(true);
    });

    it("should be able to render a datalist", async () => {
        const wrapper = await mountFormText({ id: "text-input", datalist: ["one", "two", "three"] });
        let el = wrapper.find("datalist");
        expect(el.exists()).toBe(true);
        el = wrapper.find("option");
        expect(el.exists()).toBe(true);
        el = wrapper.find("[list='text-input-datalist']");
        expect(el.exists()).toBe(true);
    });

    it("should be able to render border and text color from props", async () => {
        const wrapper = await mountFormText({});
        // Test on the b-form-input component directly since rendering is inconsistent
        const el = wrapper.find("b-form-input");
        expect(el.exists()).toBe(true);
        expect(el.attributes("style")).toBeFalsy();
        await wrapper.setProps({ color: "green" });
        expect(el.attributes("style")).toContain("color: green");
        expect(el.attributes("style")).toContain("border-color: green");
        await wrapper.setProps({ cls: "my-custom-class" });
        expect(el.classes()).toContain("my-custom-class");
    });

    it("should be able to accept a default value", async () => {
        const v = "something";
        const wrapper = await mountFormText({ value: v });
        // When value is provided, b-form-input stays as component
        const el = wrapper.find("b-form-input");
        expect(el.attributes("modelvalue")).toEqual(v);
    });

    it("should be able to accept an array as value", async () => {
        const v = ["field_1", "field_2", "field_3"];
        const wrapper = await mountFormText({ value: v });
        const el = wrapper.find("b-form-input");
        expect(el.attributes("modelvalue")).toEqual("field_1");
        await wrapper.setProps({ multiple: true });
        const elMultiple = wrapper.find("b-form-textarea");
        expect(elMultiple.attributes("modelvalue")).toEqual("field_1\nfield_2\nfield_3\n");
    });

    it("should be able to accept an empty array as value", async () => {
        const v = [];
        const wrapper = await mountFormText({ value: v });
        const el = wrapper.find("b-form-input");
        expect(el.attributes("modelvalue")).toEqual("");
    });
});
