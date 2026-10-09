import { getFakeCollectionSummary } from "@tests/test-data/collections";
import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, shallowMount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import CollectionDescription from "./CollectionDescription.vue";

enableAutoUnmount(afterEach);

describe("CollectionDescription", () => {
    it.each([
        {
            name: "heterogeneous list with one dataset",
            collectionType: "list",
            elementCount: 1,
            datatypes: ["txt", "csv", "tabular"],
            description: "a list with 1 dataset",
        },
        {
            name: "pair with no datatype",
            collectionType: "paired",
            elementCount: 2,
            datatypes: [],
            description: "a pair with 2 datasets",
        },
        {
            name: "list with no datatype",
            collectionType: "list",
            elementCount: 10,
            datatypes: [],
            description: "a list with 10 datasets",
        },
        {
            name: "list of pairs with no datatype",
            collectionType: "list:paired",
            elementCount: 10,
            datatypes: [],
            description: "a list with 10 pairs",
        },
        {
            name: "list of lists with no datatype",
            collectionType: "list:list",
            elementCount: 10,
            datatypes: [],
            description: "a list with 10 lists",
        },
        {
            name: "unknown collection with no datatype",
            collectionType: "other",
            elementCount: 10,
            datatypes: [],
            description: "a collection with 10 dataset collections",
        },
        {
            name: "homogeneous list with one dataset",
            collectionType: "list",
            elementCount: 1,
            datatypes: ["tabular"],
            description: "a list with 1 tabular dataset",
        },
        {
            name: "homogeneous pair",
            collectionType: "paired",
            elementCount: 2,
            datatypes: ["tabular"],
            description: "a pair with 2 tabular datasets",
        },
        {
            name: "homogeneous list",
            collectionType: "list",
            elementCount: 10,
            datatypes: ["tabular"],
            description: "a list with 10 tabular datasets",
        },
        {
            name: "homogeneous list of pairs",
            collectionType: "list:paired",
            elementCount: 10,
            datatypes: ["tabular"],
            description: "a list with 10 tabular pairs",
        },
        {
            name: "homogeneous list of lists",
            collectionType: "list:list",
            elementCount: 10,
            datatypes: ["tabular"],
            description: "a list with 10 tabular lists",
        },
        {
            name: "homogeneous nested pair",
            collectionType: "paired:paired",
            elementCount: 10,
            datatypes: ["tabular"],
            description: "a nested collection with 10 tabular dataset collections",
        },
        {
            name: "homogeneous unknown collection",
            collectionType: "other",
            elementCount: 10,
            datatypes: ["tabular"],
            description: "a collection with 10 tabular dataset collections",
        },
    ])("updates the description for $name", async ({ collectionType, elementCount, datatypes, description }) => {
        const hdca = getFakeCollectionSummary({ element_count: null, elements_datatypes: [] });
        const wrapper = shallowMount(CollectionDescription, {
            props: { hdca },
            global: getLocalVue(),
        });

        await wrapper.setProps({
            hdca: {
                ...hdca,
                collection_type: collectionType,
                element_count: elementCount,
                elements_datatypes: datatypes,
            },
        });

        expect(wrapper.text()).toBe(description);
    });

    function mountDescription() {
        return shallowMount(CollectionDescription, {
            props: { hdca: getFakeCollectionSummary({ elements_datatypes: [] }) },
            global: getLocalVue(),
        });
    }

    async function describeType(
        wrapper: ReturnType<typeof mountDescription>,
        collectionType: string,
        elementCount: number,
    ) {
        await wrapper.setProps({
            hdca: { ...wrapper.props("hdca"), collection_type: collectionType, element_count: elementCount },
        });
        return wrapper.text();
    }

    it("keeps the wording of sample sheets and mixed lists", async () => {
        const wrapper = mountDescription();
        expect(await describeType(wrapper, "sample_sheet", 4)).toBe("a sample sheet with 4 datasets");
        expect(await describeType(wrapper, "sample_sheet:paired", 4)).toBe("a sample sheet with 4 pairs");
        expect(await describeType(wrapper, "list:paired_or_unpaired", 4)).toBe(
            "a list with 4 paired and unpaired datasets",
        );
        expect(await describeType(wrapper, "list:paired_or_unpaired", 1)).toBe(
            "a list with 1 dataset pair or unpaired dataset",
        );
        expect(await describeType(wrapper, "sample_sheet:paired_or_unpaired", 4)).toBe(
            "a sample sheet with 4 paired and unpaired datasets",
        );
        expect(await describeType(wrapper, "list:list:list", 3)).toBe("a nested list with 3 dataset collections");
    });

    it("names records and the elements of nested lists", async () => {
        const wrapper = mountDescription();
        expect(await describeType(wrapper, "record", 2)).toBe("a record with 2 datasets");
        expect(await describeType(wrapper, "list:record", 3)).toBe("a list with 3 records");
        expect(await describeType(wrapper, "list:record", 1)).toBe("a list with 1 record");
        expect(await describeType(wrapper, "sample_sheet:record", 3)).toBe("a sample sheet with 3 records");
        expect(await describeType(wrapper, "list:list:paired", 3)).toBe("a nested list with 3 lists of pairs");
        expect(await describeType(wrapper, "list:list:paired", 1)).toBe("a nested list with 1 list of pairs");
    });

    it("names the collection type on hover", async () => {
        const wrapper = mountDescription();
        await describeType(wrapper, "list:record", 3);
        expect(wrapper.find(".description").attributes("title")).toBe("List of Records (list:record)");
        await describeType(wrapper, "paired:paired", 3);
        expect(wrapper.find(".description").attributes("title")).toBe("paired:paired");
    });
});
