import Vue from "vue";
import { mount } from "@vue/test-utils";
import PairedListCollectionCreator from "components/Collections/PairedListCollectionCreator";
import DATA from "../../../tests/qunit/test-data/paired-collection-creator.data.js";
import { getNewAttachNode } from "jest/helpers";

describe("PairedListCollectionCreator", () => {
    let wrapper;

    beforeEach(async () => {
        wrapper = mount(PairedListCollectionCreator, {
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
            attachTo: getNewAttachNode(),
        });
        await Vue.nextTick();
    });

    afterEach(async () => {
        await Vue.nextTick();
    });

    it("autopairs the dataset", async () => {
        // Autopair is called on startup
        expect(wrapper.findAll("li.dataset").length == 0).toBeTruthy();
    });
});
