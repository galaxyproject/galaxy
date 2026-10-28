import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type VueWrapper } from "@vue/test-utils";
import { beforeEach, describe, expect, it } from "vitest";

import type { HDCASummary } from "@/api";

import CollectionDescription from "./CollectionDescription.vue";

const localVue = getLocalVue();

const defaultTestHDCA: HDCASummary = {
    id: "test_id",
    name: "Test Collection",
    hid: 1,
    collection_id: "test_collection_id",
    type: "collection",
    collection_type: "list",
    history_content_type: "dataset_collection",
    element_count: null,
    create_time: "2020-01-01T00:00:00",
    update_time: null,
    deleted: false,
    visible: true,
    elements_datatypes: [],
    elements_deleted: 0,
    elements_purged: 0,
    elements_states: {},
    history_id: "fake_history_id",
    model_class: "HistoryDatasetCollectionAssociation",
    populated_state: "ok",
    tags: [],
    url: "fake/url",
    contents_url: "fake/contents/url",
};

describe("CollectionDescription", () => {
    let wrapper: VueWrapper;

    beforeEach(() => {
        wrapper = mount(CollectionDescription as object, {
            props: {
                hdca: defaultTestHDCA,
            },
            global: localVue,
        });
    });

    it("should display expected heterogeneous descriptions", async () => {
        const HETEROGENEOUS_DATATYPES = ["txt", "csv", "tabular"];
        await wrapper.setProps({
            hdca: {
                ...defaultTestHDCA,
                collection_type: "list",
                element_count: 1,
                elements_datatypes: HETEROGENEOUS_DATATYPES,
            },
        });
        expect(wrapper.text()).toBe("a list with 1 dataset");

        await wrapper.setProps({
            hdca: {
                ...defaultTestHDCA,
                element_count: 2,
                collection_type: "paired",
            },
        });
        expect(wrapper.text()).toBe("a pair with 2 datasets");

        await wrapper.setProps({
            hdca: {
                ...defaultTestHDCA,
                element_count: 10,
                collection_type: "list",
            },
        });
        expect(wrapper.text()).toBe("a list with 10 datasets");

        await wrapper.setProps({
            hdca: {
                ...defaultTestHDCA,
                element_count: 10,
                collection_type: "list:paired",
            },
        });
        expect(wrapper.text()).toBe("a list with 10 pairs");

        await wrapper.setProps({
            hdca: {
                ...defaultTestHDCA,
                element_count: 10,
                collection_type: "list:list",
            },
        });
        expect(wrapper.text()).toBe("a list with 10 lists");

        await wrapper.setProps({
            hdca: {
                ...defaultTestHDCA,
                element_count: 10,
                collection_type: "other",
            },
        });
        expect(wrapper.text()).toBe("a collection with 10 dataset collections");
    });

    it("should display expected homogeneous descriptions", async () => {
        const EXPECTED_HOMOGENEOUS_DATATYPE = "tabular";
        await wrapper.setProps({
            hdca: {
                ...defaultTestHDCA,
                element_count: 1,
                elements_datatypes: [EXPECTED_HOMOGENEOUS_DATATYPE],
            },
        });
        expect(wrapper.text()).toBe(`a list with 1 ${EXPECTED_HOMOGENEOUS_DATATYPE} dataset`);

        await wrapper.setProps({
            hdca: {
                ...defaultTestHDCA,
                element_count: 2,
                collection_type: "paired",
                elements_datatypes: [EXPECTED_HOMOGENEOUS_DATATYPE],
            },
        });
        expect(wrapper.text()).toBe(`a pair with 2 ${EXPECTED_HOMOGENEOUS_DATATYPE} datasets`);

        await wrapper.setProps({
            hdca: {
                ...defaultTestHDCA,
                element_count: 10,
                collection_type: "list",
                elements_datatypes: [EXPECTED_HOMOGENEOUS_DATATYPE],
            },
        });
        expect(wrapper.text()).toBe(`a list with 10 ${EXPECTED_HOMOGENEOUS_DATATYPE} datasets`);

        await wrapper.setProps({
            hdca: {
                ...defaultTestHDCA,
                element_count: 10,
                collection_type: "list:paired",
                elements_datatypes: [EXPECTED_HOMOGENEOUS_DATATYPE],
            },
        });
        expect(wrapper.text()).toBe(`a list with 10 ${EXPECTED_HOMOGENEOUS_DATATYPE} pairs`);

        await wrapper.setProps({
            hdca: {
                ...defaultTestHDCA,
                element_count: 10,
                collection_type: "list:list",
                elements_datatypes: [EXPECTED_HOMOGENEOUS_DATATYPE],
            },
        });
        expect(wrapper.text()).toBe(`a list with 10 ${EXPECTED_HOMOGENEOUS_DATATYPE} lists`);

        await wrapper.setProps({
            hdca: {
                ...defaultTestHDCA,
                element_count: 10,
                collection_type: "paired:paired",
                elements_datatypes: [EXPECTED_HOMOGENEOUS_DATATYPE],
            },
        });
        expect(wrapper.text()).toBe(`a nested collection with 10 ${EXPECTED_HOMOGENEOUS_DATATYPE} dataset collections`);

        await wrapper.setProps({
            hdca: {
                ...defaultTestHDCA,
                element_count: 10,
                collection_type: "other",
                elements_datatypes: [EXPECTED_HOMOGENEOUS_DATATYPE],
            },
        });
        expect(wrapper.text()).toBe(`a collection with 10 ${EXPECTED_HOMOGENEOUS_DATATYPE} dataset collections`);
    });

    async function describeType(collectionType: string, elementCount: number) {
        await wrapper.setProps({
            hdca: { ...defaultTestHDCA, collection_type: collectionType, element_count: elementCount },
        });
        return wrapper.text();
    }

    it("keeps the wording of sample sheets and mixed lists", async () => {
        expect(await describeType("sample_sheet", 4)).toBe("a sample sheet with 4 datasets");
        expect(await describeType("sample_sheet:paired", 4)).toBe("a sample sheet with 4 pairs");
        expect(await describeType("list:paired_or_unpaired", 4)).toBe("a list with 4 paired and unpaired datasets");
        expect(await describeType("list:paired_or_unpaired", 1)).toBe("a list with 1 dataset pair or unpaired dataset");
        expect(await describeType("sample_sheet:paired_or_unpaired", 4)).toBe(
            "a sample sheet with 4 paired and unpaired datasets",
        );
        expect(await describeType("list:list:list", 3)).toBe("a nested list with 3 dataset collections");
    });

    it("names records and the elements of nested lists", async () => {
        expect(await describeType("record", 2)).toBe("a record with 2 datasets");
        expect(await describeType("list:record", 3)).toBe("a list with 3 records");
        expect(await describeType("list:record", 1)).toBe("a list with 1 record");
        expect(await describeType("sample_sheet:record", 3)).toBe("a sample sheet with 3 records");
        expect(await describeType("list:list:paired", 3)).toBe("a nested list with 3 lists of pairs");
        expect(await describeType("list:list:paired", 1)).toBe("a nested list with 1 list of pairs");
    });

    async function setElementCounts(states: Record<string, number>, deleted: number, purged: number) {
        await wrapper.setProps({
            hdca: { ...defaultTestHDCA, elements_states: states, elements_deleted: deleted, elements_purged: purged },
        });
    }

    it("counts purged elements separately from deleted ones", async () => {
        await setElementCounts({ ok: 4 }, 3, 1);
        expect(wrapper.find(".deleted-elements").text()).toBe("2 deleted");
        expect(wrapper.find(".purged-elements").text()).toBe("1 purged");
    });

    it("shows only the purged count when all elements are purged", async () => {
        await setElementCounts({ ok: 2 }, 2, 2);
        expect(wrapper.find(".deleted-elements").exists()).toBe(false);
        expect(wrapper.find(".purged-elements").text()).toBe("2 purged");
    });

    it("can leave out the purged count of an all-purged collection", async () => {
        await wrapper.setProps({ hideAllPurgedCount: true });
        await setElementCounts({ ok: 2 }, 2, 2);
        expect(wrapper.find(".purged-elements").exists()).toBe(false);

        await setElementCounts({ ok: 2 }, 1, 1);
        expect(wrapper.find(".purged-elements").text()).toBe("1 purged");
    });

    it("names the collection type on hover", async () => {
        await describeType("list:record", 3);
        expect(wrapper.find(".description").attributes("title")).toBe("List of Records (list:record)");
        await describeType("paired:paired", 3);
        expect(wrapper.find(".description").attributes("title")).toBe("paired:paired");
    });
});
