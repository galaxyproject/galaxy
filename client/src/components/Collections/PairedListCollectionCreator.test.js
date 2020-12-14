import Vue from "vue";
import { mount } from "@vue/test-utils";
import PairedListCollectionCreator from "components/Collections/PairedListCollectionCreator";
import DATA from "../test-data/paired-collection-creator.data";
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
        wrapper._autopair();
        expect(wrapper.workingElements.length == 0);
    });
});
