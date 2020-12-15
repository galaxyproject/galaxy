import { shallowMount } from "@vue/test-utils";
import PairedListCollectionCreator from "components/Collections/PairedListCollectionCreator";
import DATA from "../../../tests/qunit/test-data/paired-collection-creator.data.js";

describe("PairedListCollectionCreator", () => {
    let wrapper;

    beforeEach(async () => {
        wrapper = shallowMount(PairedListCollectionCreator, {
            propsData: {
                initialElements: DATA._1,
                creationFn: () => {
                    return;
                },
                oncreate: () => {
                    return;
                },
                oncancel: () => {
                    return;
                },
            },
        });
        await wrapper.vm.$nextTick();
    });

    afterEach(async () => {
        await wrapper.vm.$nextTick();
    });

    it("autopairs the dataset", async () => {
        // Autopair is called on startup
        expect(wrapper.findAll("li.dataset").length == 0).toBeTruthy();
    });
});
