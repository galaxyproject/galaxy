import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import FormText from "./FormText";

const localVue = getLocalVue();

describe("FormText", () => {
    const mountFormText = async (props) =>
        await mount(FormText, {
            propsData: props,
            localVue,
        });

    it("should render the appropriate input type", async () => {
        const wrapper = await mountFormText({});
        const el = wrapper.find("input[type='text']");
        expect(el.exists()).toBe(true);
        await wrapper.setProps({ type: "password" });
        const elPassword = wrapper.find("input[type='password']");
        expect(elPassword.exists()).toBe(true);
        await wrapper.setProps({ type: "anyothertype" });
        const elOtherType = wrapper.find("input[type='text']");
        expect(elOtherType.exists()).toBe(true);
    });

    it("should render the appropriate component", async () => {
        const wrapper = await mountFormText({ area: true });
        const el = wrapper.find("textarea");
        expect(el.exists()).toBe(true);
        await wrapper.setProps({ area: false, multiple: true });
        const elMultiple = wrapper.find("textarea");
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
        const el = wrapper.find("input");
        expect(el.element.style).toMatchObject({});
        await wrapper.setProps({ color: "green" });
        expect(el.element.style).toMatchObject({ color: "green", "border-color": "green" });
        await wrapper.setProps({ cls: "my-custom-class" });
        expect(el.element.classList).toContain("my-custom-class");
    });

    it("should be able to accept a default value", async () => {
        const v = "something";
        const wrapper = await mountFormText({ value: v });
        const el = wrapper.find("input");
        expect(el.props("value")).toEqual(v);
    });

    it("should be able to accept an array as value", async () => {
        const v = ["field_1", "field_2", "field_3"];
        const wrapper = await mountFormText({ value: v });
        const el = wrapper.find("input");
        expect(el.props("value")).toEqual("field_1");
        await wrapper.setProps({ multiple: true });
        const elMultiple = wrapper.find("textarea");
        expect(elMultiple.props("value")).toEqual("field_1\nfield_2\nfield_3\n");
    });

    it("should be able to accept an empty array as value", async () => {
        const v = [];
        const wrapper = await mountFormText({ value: v });
        const el = wrapper.find("input");
        expect(el.props("value")).toEqual("");
    });
});
