import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { disposePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, onTestFinished, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import { testDatatypesMapper } from "@/components/Datatypes/test_fixtures";
import { sanitizeHtml } from "@/directives/sanitizeHtml";
import { useDatatypesMapperStore } from "@/stores/datatypesMapperStore";

import HistoryDatasetDetails from "./HistoryDatasetDetails.vue";

const localVue = getLocalVue();

const { server, http } = useServerMock();

beforeEach(() => vi.mocked(sanitizeHtml).mockClear());
afterEach(() => vi.mocked(sanitizeHtml).mockClear());
enableAutoUnmount(afterEach);

const tabularDataset = {
    metadata_columns: 2,
    metadata_data_lines: 4,
    misc_blurb: "tabular_misc_blurb",
    extension: "tabular",
    name: "tabular_name",
    peek: "tabular_peek",
    state: "ok",
};

function setUpDatatypesStore() {
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    onTestFinished(() => disposePinia(pinia));
    const datatypesStore = useDatatypesMapperStore(pinia);
    datatypesStore.datatypesMapper = testDatatypesMapper;
    return pinia;
}

async function mountDatasetDetails(props, dataset = tabularDataset) {
    server.use(http.get("/api/datasets/{dataset_id}", ({ response }) => response(200).json(dataset)));
    const wrapper = mount(HistoryDatasetDetails, {
        global: withPlugins(localVue, setUpDatatypesStore()),
        props,
    });
    await flushPromises();
    return wrapper;
}

describe("HistoryDatasetDetails.vue", () => {
    it("updates the displayed attribute from peek to name, information, and datatype", async () => {
        const wrapper = await mountDatasetDetails({ datasetId: "datasetId", name: "history_dataset_peek" });
        expect(wrapper.text()).toBe("tabular_peek");
        await wrapper.setProps({ name: "history_dataset_name" });
        expect(wrapper.text()).toBe("tabular_name");
        await wrapper.setProps({ name: "history_dataset_info" });
        expect(wrapper.text()).toBe("tabular_misc_blurb");
        await wrapper.setProps({ name: "history_dataset_type" });
        expect(wrapper.text()).toBe("tabular");
    });

    it("shows the dataset name as text and renders the peek through v-sanitize-html", async () => {
        const dataset = { ...tabularDataset, name: "<b>name</b>", peek: "<table><tr><td>peek</td></tr></table>" };
        const wrapper = await mountDatasetDetails({ datasetId: "datasetId", name: "history_dataset_name" }, dataset);
        expect(wrapper.get("pre").text()).toBe("<b>name</b>");
        expect(wrapper.find("b").exists()).toBe(false);
        expect(sanitizeHtml).not.toHaveBeenCalled();

        await wrapper.setProps({ name: "history_dataset_peek" });
        expect(sanitizeHtml).toHaveBeenCalledWith(dataset.peek, "default");
        expect(wrapper.get("pre td").text()).toBe("peek");
    });
});
