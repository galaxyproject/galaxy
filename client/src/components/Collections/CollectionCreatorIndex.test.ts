import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { createHistoryDatasetCollectionInstanceFull } from "@/api/datasetCollections";
import { useHistoryItemsStore } from "@/stores/historyItemsStore";

import CollectionCreatorIndex from "./CollectionCreatorIndex.vue";

vi.mock("@/api/datasetCollections", async (importOriginal) => ({
    ...((await importOriginal()) as Record<string, unknown>),
    createHistoryDatasetCollectionInstanceFull: vi.fn(),
}));

vi.mock("@/composables/useHistoryDatasets", () => ({
    useHistoryDatasets: () => ({
        datasets: ref([]),
        isFetching: ref(false),
        error: ref(null),
        initialFetchDone: ref(true),
        history: ref(null),
    }),
}));

const createCollection = vi.mocked(createHistoryDatasetCollectionInstanceFull);

const CREATED_COLLECTION = { id: "hdca-1", history_content_type: "dataset_collection", state: "ok" };

function mountCreatorIndex() {
    const pinia = createTestingPinia({ createSpy: vi.fn });
    const historyItemsStore = useHistoryItemsStore(pinia);
    // @ts-expect-error getters are writable in testing pinia
    historyItemsStore.getHistoryItems = () => [CREATED_COLLECTION];

    return mount(CollectionCreatorIndex as object, {
        props: {
            historyId: "history-1",
            show: true,
            notModal: true,
            collectionType: "list",
            extendedCollectionType: {},
        },
        global: {
            ...withPlugins(getLocalVue(), pinia),
            stubs: { ListCollectionCreator: true, GenericItem: true },
        },
    });
}

async function submitCreator(wrapper: ReturnType<typeof mountCreatorIndex>) {
    wrapper.findComponent({ name: "ListCollectionCreator" }).vm.$emit("on-create", {});
    await flushPromises();
}

function findLinkByText(wrapper: ReturnType<typeof mountCreatorIndex>, text: string) {
    const link = wrapper.findAll(".g-link").find((element) => element.text() === text);
    if (!link) {
        throw new Error(`No link with text "${text}"`);
    }
    return link;
}

describe("CollectionCreatorIndex", () => {
    beforeEach(() => {
        createCollection.mockReset();
    });

    it("offers a 'Try again' button after a failed create that brings back the creator", async () => {
        createCollection.mockRejectedValue("Collection name is invalid");
        const wrapper = mountCreatorIndex();

        await submitCreator(wrapper);

        expect(wrapper.text()).toContain("Collection name is invalid");
        expect(wrapper.findComponent({ name: "ListCollectionCreator" }).exists()).toBe(false);

        const retry = findLinkByText(wrapper, "Try again");
        expect(retry.element.tagName).toBe("BUTTON");

        await retry.trigger("click");

        expect(wrapper.text()).not.toContain("Collection name is invalid");
        expect(wrapper.findComponent({ name: "ListCollectionCreator" }).exists()).toBe(true);
    });

    it("offers a 'Create another collection' button after a successful create", async () => {
        createCollection.mockResolvedValue(CREATED_COLLECTION as never);
        const wrapper = mountCreatorIndex();

        await submitCreator(wrapper);

        expect(wrapper.text()).toContain("Collection created successfully.");

        const another = findLinkByText(wrapper, "Create another collection");
        expect(another.element.tagName).toBe("BUTTON");

        await another.trigger("click");

        expect(wrapper.text()).not.toContain("Collection created successfully.");
        expect(wrapper.findComponent({ name: "ListCollectionCreator" }).exists()).toBe(true);
    });
});
