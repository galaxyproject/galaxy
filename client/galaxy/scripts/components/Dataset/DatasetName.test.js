import { mount } from "@vue/test-utils";
import DatasetName from "./DatasetName";

describe("Dataset Name", () => {
    it("test dataset default", async () => {
        const wrapper = mount(DatasetName, { propsData: { item: { name: "name", state: "success" } } });
        const state = wrapper.findAll(".name");
        expect(state.length).to.equal(1);
        expect(state.at(0).text()).to.equal("name");
        const $linkShow = wrapper.find(".dropdown-item:first-child");
        $linkShow.trigger("click");
        expect(wrapper.emitted().showDataset).to.be.an("array");
        const $linkCopy = wrapper.find(".dropdown-item:last-child");
        $linkCopy.trigger("click");
        expect(wrapper.emitted().copyDataset).to.be.an("array");
    });
    it("test dataset error", async () => {
        const wrapper = mount(DatasetName, { propsData: { item: { name: "name", state: "error" } } });
        const state = wrapper.findAll(".name");
        expect(state.length).to.equal(1);
        expect(state.at(0).text()).to.equal("name");
        const errorstate = wrapper.findAll(".error");
        expect(errorstate.length).to.equal(1);
        expect(errorstate.at(0).classes()).to.include("text-danger");
    });
    it("test dataset paused", async () => {
        const wrapper = mount(DatasetName, { propsData: { item: { name: "name", state: "paused" } } });
        const state = wrapper.findAll(".name");
        expect(state.length).to.equal(1);
        expect(state.at(0).text()).to.equal("name");
        const pausestate = wrapper.findAll(".pause");
        expect(pausestate.length).to.equal(1);
        expect(pausestate.at(0).classes()).to.include("text-info");
    });
});
