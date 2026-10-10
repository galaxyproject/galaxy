import { createTestingPinia } from "@pinia/testing";
import { getFakeHistorySummary } from "@tests/test-data";
import { getFakeDatasetSummary } from "@tests/test-data/datasets";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";
import Multiselect from "vue-multiselect";

import { useServerMock } from "@/api/client/__mocks__";
import { useEventStore } from "@/stores/eventStore";
import { seedCurrentHistory } from "@/stores/testUtils";

import SelectionField from "./SelectionField.vue";

const localVue = getLocalVue();
const { server, http } = useServerMock();

const HISTORY_ID = "history123";
const DATASET = getFakeDatasetSummary({ id: "ds1", name: "Dataset A", history_id: HISTORY_ID });

/** Waits out the component's 300 ms search debounce and the search it starts. */
async function waitForDebouncedSearch() {
    await new Promise((resolve) => setTimeout(resolve, 350));
    await flushPromises();
}

/**
 * Serves the current history's datasets search, answering with `datasets` or, when
 * `errorMessage` is given, a Galaxy error. Returns the query parameters of each request.
 */
function serveDatasets({ datasets = [DATASET], errorMessage = null } = {}) {
    const searches = [];
    server.use(
        http.get("/api/datasets", ({ query, response }) => {
            searches.push({ historyId: query.get("history_id"), text: query.get("qv") });
            if (errorMessage) {
                return response("5XX").json({ err_msg: errorMessage, err_code: 500 }, { status: 500 });
            }
            return response(200).json(datasets);
        }),
    );
    return searches;
}

/** Mounts a dataset selection field with `HISTORY_ID` as the current history. */
function mountSelectionField(props = {}) {
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    seedCurrentHistory(getFakeHistorySummary({ id: HISTORY_ID }), pinia);
    const wrapper = mount(SelectionField, {
        global: withPlugins(localVue, pinia),
        props: { objectType: "history_dataset_id", ...props },
    });
    return { wrapper, eventStore: useEventStore(pinia) };
}

describe("SelectionField", () => {
    it("renders the label and multiselect once datasets are loaded", async () => {
        serveDatasets();
        const { wrapper } = mountSelectionField({ objectName: "My Dataset", objectId: "ds1" });
        await waitForDebouncedSearch();

        const label = wrapper.find("label");
        expect(label.exists()).toBe(true);
        expect(label.text()).toContain("Select a History Dataset Id");
        expect(wrapper.findComponent(Multiselect).exists()).toBe(true);
    });

    it("renders an empty state when the current history has no datasets", async () => {
        serveDatasets({ datasets: [] });
        const { wrapper } = mountSelectionField();
        await waitForDebouncedSearch();

        expect(wrapper.text()).toContain("No datasets found in your current history");
    });

    it("searches the current history's datasets when the search text changes", async () => {
        const searches = serveDatasets();
        const { wrapper } = mountSelectionField();
        await waitForDebouncedSearch();

        const multiselect = wrapper.findComponent(Multiselect);
        expect(multiselect.exists()).toBe(true);
        multiselect.vm.$emit("search-change", "abc");
        await waitForDebouncedSearch();

        expect(searches).toContainEqual({ historyId: HISTORY_ID, text: "abc" });
    });

    it("shows the error when the dataset search fails", async () => {
        serveDatasets({ errorMessage: "Oops!" });
        const { wrapper } = mountSelectionField();
        await waitForDebouncedSearch();

        expect(wrapper.text()).toContain("Oops!");
    });

    it("highlights a dragged dataset and emits it as the selection when dropped", async () => {
        serveDatasets();
        const { wrapper, eventStore } = mountSelectionField();
        await waitForDebouncedSearch();
        eventStore.setDragData({ id: "item1", name: "Item One", history_content_type: "dataset" });

        expect(wrapper.classes()).not.toContain("ui-dragover-success");
        await wrapper.trigger("dragenter");
        expect(wrapper.classes()).toContain("ui-dragover-success");
        await wrapper.trigger("drop");
        expect(wrapper.classes()).not.toContain("ui-dragover-success");
        expect(wrapper.emitted("change")).toEqual([[{ id: "item1", name: "Item One" }]]);
    });

    it("searches with the custom objectQuery function when provided", async () => {
        const objectQuery = vi.fn(() => Promise.resolve([{ id: "custom1", name: "Custom Result" }]));
        const { wrapper } = mountSelectionField({ objectQuery });
        await waitForDebouncedSearch();

        wrapper.findComponent(Multiselect).vm.$emit("search-change", "test");
        await waitForDebouncedSearch();

        expect(objectQuery).toHaveBeenCalledWith("test");
    });

    it("selects the first dataset when no objectId and objectName are given", async () => {
        serveDatasets();
        const { wrapper } = mountSelectionField({ objectId: "", objectName: "" });
        await waitForDebouncedSearch();

        const multiselect = wrapper.findComponent(Multiselect);
        expect(multiselect.exists()).toBe(true);
        expect(multiselect.props("options")).toHaveLength(1);
        expect(multiselect.props("modelValue")).toEqual({ id: "ds1", name: "Dataset A" });
        expect(multiselect.find(".multiselect__single").text()).toBe("Dataset A");
    });
});
