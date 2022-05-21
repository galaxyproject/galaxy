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
            },
            localVue,
        });
    });

    it("should display expected heterogeneous descriptions", async () => {
        const HETEROGENEOUS_DATATYPES = ["txt", "csv", "tabular"];
        await wrapper.setProps({ elementCount: 1, elementsDatatypes: HETEROGENEOUS_DATATYPES });
        expect(wrapper.text()).toBe("a list with 1 dataset");

        await wrapper.setProps({ elementCount: 2, collectionType: "paired" });
        expect(wrapper.text()).toBe("a pair with 2 datasets");

        await wrapper.setProps({ elementCount: 10, collectionType: "list" });
        expect(wrapper.text()).toBe("a list with 10 datasets");

        await wrapper.setProps({ collectionType: "list:paired" });
        expect(wrapper.text()).toBe("a list with 10 pairs");

        await wrapper.setProps({ collectionType: "list:list" });
        expect(wrapper.text()).toBe("a list with 10 lists");

        await wrapper.setProps({ collectionType: "other" });
        expect(wrapper.text()).toBe("a nested list with 10 dataset collections");
    });

    it("should display expected homogeneous descriptions", async () => {
        const EXPECTED_HOMOGENEOUS_DATATYPE = "tabular";
        await wrapper.setProps({ elementCount: 1, elementsDatatypes: [EXPECTED_HOMOGENEOUS_DATATYPE] });
        expect(wrapper.text()).toBe(`a list with 1 ${EXPECTED_HOMOGENEOUS_DATATYPE} dataset`);

        await wrapper.setProps({ elementCount: 2, collectionType: "paired" });
        expect(wrapper.text()).toBe(`a pair with 2 ${EXPECTED_HOMOGENEOUS_DATATYPE} datasets`);

        await wrapper.setProps({ elementCount: 10, collectionType: "list" });
        expect(wrapper.text()).toBe(`a list with 10 ${EXPECTED_HOMOGENEOUS_DATATYPE} datasets`);

        await wrapper.setProps({ collectionType: "list:paired" });
        expect(wrapper.text()).toBe(`a list with 10 ${EXPECTED_HOMOGENEOUS_DATATYPE} pairs`);

        await wrapper.setProps({ collectionType: "list:list" });
        expect(wrapper.text()).toBe(`a list with 10 ${EXPECTED_HOMOGENEOUS_DATATYPE} lists`);

        await wrapper.setProps({ collectionType: "other" });
        expect(wrapper.text()).toBe(`a nested list with 10 ${EXPECTED_HOMOGENEOUS_DATATYPE} dataset collections`);
    });
});
