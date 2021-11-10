import DatasetCollectionUIWrapper from "./DatasetCollectionUIWrapper";
import DscUI from "components/History/ContentItem/DatasetCollection/DscUI";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import datasetCollectionRaw from "components/History/test/json/DatasetCollection.json";
import datasetCollectionContent from "components/History/test/json/DatasetCollection.nested.json";

jest.mock("components/History/caching");

describe("DatasetUIWrapper.vue with Dataset", () => {
    let wrapper;
    let propsData;
    let onHide;
    let onUnhide;
    let onDelete;
    let onUndelete;

    beforeEach(async () => {
        propsData = {
            item: datasetCollectionRaw,
        };
        onHide = jest.spyOn(DatasetCollectionUIWrapper.methods, "onHide").mockImplementation();
        onUnhide = jest.spyOn(DatasetCollectionUIWrapper.methods, "onUnhide").mockImplementation();
        onDelete = jest.spyOn(DatasetCollectionUIWrapper.methods, "onDelete").mockImplementation();
        onUndelete = jest.spyOn(DatasetCollectionUIWrapper.methods, "onUndelete").mockImplementation();
        wrapper = shallowMount(DatasetCollectionUIWrapper, {
            propsData,
        });
    });

    it("loads DscUI component", async () => {
        expect(wrapper.findComponent(DscUI).exists()).toBeTruthy();
    });

    it("reacts to all emittted events", async () => {
        expect(onHide).not.toHaveBeenCalled();
        expect(onUnhide).not.toHaveBeenCalled();
        expect(onDelete).not.toHaveBeenCalled();
        expect(onUndelete).not.toHaveBeenCalled();
        wrapper.findComponent(DscUI).vm.$emit("hide");
        expect(onHide).toHaveBeenCalled();
        wrapper.findComponent(DscUI).vm.$emit("unhide");
        expect(onUnhide).toHaveBeenCalled();
        wrapper.findComponent(DscUI).vm.$emit("delete");
        expect(onDelete).toHaveBeenCalled();
        wrapper.findComponent(DscUI).vm.$emit("undelete");
        expect(onUndelete).toHaveBeenCalled();
    });
    it("creates DatasetCollection", async () => {
        const datasetCollection = wrapper.vm.datasetCollection;
        expect(datasetCollection.collectionType).toBe("list of pairs");
    });
    it("manages collection expansion", async () => {
        expect(wrapper.vm.expand).toBeFalsy();
        wrapper.findComponent(DscUI).vm.$emit("viewCollection", wrapper.vm.datasetCollection);
        expect(wrapper.vm.expand).toBeTruthy();
    });
    it("build dsc from collection content", async () => {
        wrapper.setProps({ item: datasetCollectionContent });
        await flushPromises();
        expect(wrapper.vm.datasetCollection.name).toBe(datasetCollectionContent.element_identifier);
    });
});
