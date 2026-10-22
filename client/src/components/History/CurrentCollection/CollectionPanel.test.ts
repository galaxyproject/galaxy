import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { reactive } from "vue";

import type { DCESummary, HDASummary, HDCASummary, HistorySummary } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";

import CollectionPanel from "./CollectionPanel.vue";
import ListingLayout from "@/components/History/Layout/ListingLayout.vue";

const localVue = getLocalVue();

const { server, http } = useServerMock();

const NUM_ELEMENTS = 3;

let elementsState = "running";
const fetchElementsSpy = vi.fn();

const history: HistorySummary = {
    id: "history-id",
    name: "History",
    model_class: "History",
    annotation: null,
    count: 0,
    deleted: false,
    purged: false,
    archived: false,
    published: false,
    tags: [],
    update_time: "2026-10-22T10:00:00.000Z",
    url: "",
};

function mockCollection(): HDCASummary {
    // Reactive like the history items the panel receives from the store.
    return reactive({
        id: "hdca-id",
        element_count: NUM_ELEMENTS,
        elements_datatypes: ["txt"],
        elements_deleted: 0,
        elements_states: { running: NUM_ELEMENTS },
        collection_type: "list",
        populated_state: "ok",
        populated_state_message: "",
        collection_id: "dc-id",
        name: "collection",
        deleted: false,
        contents_url: "",
        hid: 1,
        history_content_type: "dataset_collection",
        history_id: history.id,
        model_class: "HistoryDatasetCollectionAssociation",
        tags: [],
        visible: true,
        create_time: "2026-10-22T10:00:00.000Z",
        update_time: "2026-10-22T10:00:00.000Z",
        type_id: "dataset_collection",
        url: "",
        type: "collection",
        store_times_summary: null,
    });
}

function mockElement(i: number): DCESummary {
    return {
        id: `dce-${i}`,
        element_index: i,
        element_identifier: `element ${i}`,
        element_type: "hda",
        model_class: "DatasetCollectionElement",
        object: {
            id: `hda-${i}`,
            model_class: "HistoryDatasetAssociation",
            state: elementsState,
            hda_ldda: "hda",
            history_id: history.id,
            tags: [],
            accessible: true,
            purged: false,
        },
    } as DCESummary;
}

function mountPanel(collection: HDCASummary) {
    return shallowMount(CollectionPanel as object, {
        localVue,
        propsData: { history, selectedCollections: [collection] },
    });
}

async function waitForFetch() {
    // Element fetches are throttled by the store's queue.
    await vi.advanceTimersByTimeAsync(1500);
    await flushPromises();
}

function renderedStates(wrapper: ReturnType<typeof mountPanel>) {
    const items: DCESummary[] = wrapper.findComponent(ListingLayout).props("items");
    return items.map((item) => (item.object as HDASummary).state);
}

describe("CollectionPanel", () => {
    beforeEach(() => {
        vi.useFakeTimers();
        setActivePinia(createTestingPinia({ createSpy: vi.fn, stubActions: false }));
        elementsState = "running";
        fetchElementsSpy.mockClear();
        server.use(
            http.get("/api/dataset_collections/{hdca_id}/contents/{parent_id}", ({ response }) => {
                fetchElementsSpy();
                return response(200).json(Array.from({ length: NUM_ELEMENTS }, (_, i) => mockElement(i)));
            }),
        );
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it("refreshes cached elements when the collection is opened again", async () => {
        const collection = mockCollection();
        const firstVisit = mountPanel(collection);
        await waitForFetch();
        expect(renderedStates(firstVisit)).toEqual(["running", "running", "running"]);
        firstVisit.destroy();

        elementsState = "ok";
        const secondVisit = mountPanel(collection);
        await waitForFetch();

        expect(fetchElementsSpy).toHaveBeenCalledTimes(2);
        expect(renderedStates(secondVisit)).toEqual(["ok", "ok", "ok"]);
    });

    it("refreshes elements when the collection is updated while it is open", async () => {
        const collection = mockCollection();
        const wrapper = mountPanel(collection);
        await waitForFetch();
        expect(renderedStates(wrapper)).toEqual(["running", "running", "running"]);

        // The history watcher merges the updated collection into the same object, replacing its nested objects.
        collection.elements_states = { running: NUM_ELEMENTS };
        await waitForFetch();
        expect(fetchElementsSpy).toHaveBeenCalledTimes(1);

        elementsState = "ok";
        collection.elements_states = { ok: NUM_ELEMENTS };
        await waitForFetch();

        expect(fetchElementsSpy).toHaveBeenCalledTimes(2);
        expect(renderedStates(wrapper)).toEqual(["ok", "ok", "ok"]);
    });
});
