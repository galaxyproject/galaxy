import { deferred } from "@tests/vitest/deferred";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { loadDatasets } from "@/api/datasets";
import { updateTags } from "@/api/tags";

import DatasetList from "./DatasetList.vue";
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";

vi.mock("@/api/datasets", async (importOriginal) => ({
    ...(await importOriginal<object>()),
    loadDatasets: vi.fn(),
}));

vi.mock("@/api/tags", () => ({
    updateTags: vi.fn(),
}));

const DATASET = {
    id: "dataset-1",
    name: "reads.fastq",
    tags: [],
    history_id: "history-1",
    history_content_type: "dataset",
    extension: "fastqsanger",
    state: "ok",
    deleted: false,
    visible: true,
    hid: 1,
    update_time: "2026-01-01T00:00:00",
};

// an HDA and an HDCA can share an encoded id
const COLLECTION = {
    ...DATASET,
    name: "paired reads",
    history_content_type: "dataset_collection",
    hid: 2,
};

async function mountList(items: object[] = [DATASET]) {
    vi.mocked(loadDatasets).mockResolvedValue({
        data: items.map((item) => ({ ...item })),
        totalMatches: items.length,
    } as never);
    const wrapper = mount(DatasetList as object, {
        global: {
            ...getLocalVue(),
            stubs: {
                BreadcrumbHeading: true,
                DelayedInput: true,
                ListHeader: true,
                SelectorModal: true,
                StatelessTags: true,
                SwitchToHistoryLink: true,
                UtcDate: true,
            },
        },
    });
    await flushPromises();
    return wrapper;
}

describe("DatasetList", () => {
    beforeEach(() => {
        vi.mocked(updateTags).mockReset();
    });

    it("saves the tag edits of a dataset one after another", async () => {
        const saves = [deferred<void>(), deferred<void>()];
        vi.mocked(updateTags).mockImplementation(() => saves[vi.mocked(updateTags).mock.calls.length - 1]!.promise);
        const wrapper = await mountList();

        const tags = wrapper.findComponent(StatelessTags);
        tags.vm.$emit("update:modelValue", ["first"]);
        tags.vm.$emit("update:modelValue", ["first", "second"]);
        await flushPromises();
        expect(updateTags).toHaveBeenCalledTimes(1);
        expect(updateTags).toHaveBeenLastCalledWith("dataset-1", "HistoryDatasetAssociation", ["first"]);
        expect(tags.props("modelValue")).toEqual(["first", "second"]);

        saves[0]!.resolve();
        await flushPromises();
        expect(updateTags).toHaveBeenCalledTimes(2);
        expect(updateTags).toHaveBeenLastCalledWith("dataset-1", "HistoryDatasetAssociation", ["first", "second"]);
        saves[1]!.resolve();
        await flushPromises();
        expect(tags.props("modelValue")).toEqual(["first", "second"]);
    });

    it("keeps the tags and saves of a dataset and a collection with the same id apart", async () => {
        const saves = [deferred<void>(), deferred<void>()];
        vi.mocked(updateTags).mockImplementation(() => saves[vi.mocked(updateTags).mock.calls.length - 1]!.promise);
        const wrapper = await mountList([DATASET, COLLECTION]);

        const [datasetTags, collectionTags] = wrapper.findAllComponents(StatelessTags);
        collectionTags!.vm.$emit("update:modelValue", ["pair"]);
        datasetTags!.vm.$emit("update:modelValue", ["single"]);
        await flushPromises();
        expect(updateTags).toHaveBeenCalledTimes(2);
        expect(updateTags).toHaveBeenCalledWith("dataset-1", "HistoryDatasetCollectionAssociation", ["pair"]);
        expect(updateTags).toHaveBeenCalledWith("dataset-1", "HistoryDatasetAssociation", ["single"]);
        expect(collectionTags!.props("modelValue")).toEqual(["pair"]);
        expect(datasetTags!.props("modelValue")).toEqual(["single"]);

        saves[0]!.resolve();
        saves[1]!.resolve();
        await flushPromises();
        expect(collectionTags!.props("modelValue")).toEqual(["pair"]);
        expect(datasetTags!.props("modelValue")).toEqual(["single"]);
    });
});
