import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue } from "jest/helpers";
import FormText from "./FormText";

const localVue = getLocalVue();

describe("FormText", () => {
    const mountFormText = async (props) =>
        await mount(FormText, {
            propsData: props,
            localVue,
        });

    // constants
    const getAlert = async (wrapper) => await wrapper.find("[role='alert']");

    it("should render the appropriate input type", async () => {
        let wrapper = await mountFormText({});
        await flushPromises();
        let el = await wrapper.find("input[type='text']");
        expect(el.exists()).toBe(true);

        wrapper = await mountFormText({ type: "password" });
        await flushPromises();
        el = await wrapper.find("input[type='password']");
        expect(el.exists()).toBe(true);
    });

    it("should render the appropriate component", async () => {
        let wrapper = await mountFormText({ area: true });
        await flushPromises();
        let el = await wrapper.find("textarea");
        expect(el.exists()).toBe(true);

        wrapper = await mountFormText({ multiple: true });
        await flushPromises();
        el = await wrapper.find("textarea");
        expect(el.exists()).toBe(true);
    });

    it("should be able to render a datalist", async () => {
        let wrapper = await mountFormText({ datalist: ["one", "two", "three"] });
        await flushPromises();
        let el = await wrapper.find("datalist");
        expect(el.exists()).toBe(true);
        el = await wrapper.find("option");
        expect(el.exists()).toBe(true);
    });

    it("should be able to render style from props", async () => {
        let wrapper = await mountFormText({ styleObj: { fontSize: "18px" } });
        await flushPromises();
        let el = await wrapper.find("input");
        expect(el.element.style).toMatchObject({ fontSize: "18px" });

        wrapper = await mountFormText({ styleObj: { fontSize: "18px" }, color: 'white' });
        await flushPromises();
        el = await wrapper.find("input");
        expect(el.element.style).toMatchObject({ fontSize: "18px", color: 'white' });
    });

    it("should be able to accept a default value", async () => {
        const v = "something";
        let wrapper = await mountFormText({ value: v });
        await flushPromises();
        let el = await wrapper.find("input");
        expect(el.props('value')).toEqual(v);
    });
});
