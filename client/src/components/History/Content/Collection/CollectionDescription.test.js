import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import CollectionDescription from "./CollectionDescription";

const localVue = getLocalVue();

describe("CollectionDescription", () => {
    let wrapper;

    beforeEach(() => {
        wrapper = mount(CollectionDescription, {
            propsData: {
                collectionType: "list",
                elementCount: 10,
            },
            localVue,
        });
    });

    it("check basics", async () => {
        const details = wrapper.findAll("span");
        expect(details.at(0).text()).toBe("a list");
        expect(details.at(1).text()).toBe("with 10 items");
        await wrapper.setProps({ elementCount: 1 });
        expect(details.at(1).text()).toBe("with 1 item");
        await wrapper.setProps({ collectionType: "paired" });
        expect(details.at(0).text()).toBe("a dataset pair");
        await wrapper.setProps({ collectionType: "list:paired" });
        expect(details.at(0).text()).toBe("a list of pairs");
        await wrapper.setProps({ collectionType: "other" });
        expect(details.at(0).text()).toBe("a nested list");
    });
});
