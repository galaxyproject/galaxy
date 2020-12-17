import { mount } from "@vue/test-utils";
import DatasetName from "./DatasetName";

describe("Dataset Name", () => {
    it("test dataset default", async () => {
        const wrapper = mount(DatasetName, {
            propsData: { item: { name: "name", state: "success" } },
        });
        const state = wrapper.findAll(".name");
        expect(state.length).toBe(1);
        expect(state.at(0).text()).toBe("name");
        const $linkShow = wrapper.find(".dropdown-item:first-child");
        $linkShow.trigger("click");
        expect(Array.isArray(wrapper.emitted().showDataset)).toBe(true);
        const $linkCopy = wrapper.find(".dropdown-item:last-child");
        $linkCopy.trigger("click");
        expect(Array.isArray(wrapper.emitted().copyDataset)).toBe(true);
    });
    it("test dataset error", async () => {
        const wrapper = mount(DatasetName, {
            propsData: { item: { name: "name", state: "error" } },
        });
        const state = wrapper.findAll(".name");
        expect(state.length).toBe(1);
        expect(state.at(0).text()).toBe("name");
        const errorstate = wrapper.findAll(".error");
        expect(errorstate.length).toBe(1);
        expect(errorstate.at(0).classes()).toEqual(expect.arrayContaining(["text-danger"]));
    });
    it("test dataset paused", async () => {
        const wrapper = mount(DatasetName, {
            propsData: { item: { name: "name", state: "paused" } },
        });
        const state = wrapper.findAll(".name");
        expect(state.length).toBe(1);
        expect(state.at(0).text()).toBe("name");
        const pausestate = wrapper.findAll(".pause");
        expect(pausestate.length).toBe(1);
        expect(pausestate.at(0).classes()).toEqual(expect.arrayContaining(["text-info"]));
    });
});
