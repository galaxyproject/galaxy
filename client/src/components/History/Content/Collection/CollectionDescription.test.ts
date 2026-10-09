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
});
