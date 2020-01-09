import { mount } from "@vue/test-utils";
import DatasetName from "./DatasetName";

describe("Dataset Name", () => {
    it("test dataset default", async () => {
        const wrapper = mount(DatasetName, { propsData: { item: { name: "name", state: "success" } } });
        const state = wrapper.findAll("span");
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
        const state = wrapper.findAll("span");
        expect(state.length).to.equal(2);
        expect(state.at(0).classes()).to.include("text-danger");
        expect(state.at(1).text()).to.equal("name");
    });
    it("test dataset paused", async () => {
        const wrapper = mount(DatasetName, { propsData: { item: { name: "name", state: "paused" } } });
        const state = wrapper.findAll("span");
        expect(state.length).to.equal(2);
        expect(state.at(0).classes()).to.include("text-info");
        expect(state.at(1).text()).to.equal("name");
    });
});
