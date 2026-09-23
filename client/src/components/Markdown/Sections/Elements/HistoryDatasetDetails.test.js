import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import { testDatatypesMapper } from "@/components/Datatypes/test_fixtures";
import { sanitizeHtml } from "@/directives/sanitizeHtml";
import { useDatatypesMapperStore } from "@/stores/datatypesMapperStore";

import HistoryDatasetDetails from "./HistoryDatasetDetails.vue";

const localVue = getLocalVue();

const { server, http } = useServerMock();

const tabularMetaData = {
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
    const datatypesStore = useDatatypesMapperStore();
    datatypesStore.datatypesMapper = testDatatypesMapper;
    return pinia;
}

async function mountTarget(propsData = {}, dataset = tabularMetaData) {
    server.use(http.get("/api/datasets/{dataset_id}", ({ response }) => response(200).json(dataset)));
    const wrapper = mount(HistoryDatasetDetails, {
        localVue,
        propsData,
        pinia: setUpDatatypesStore(),
    });
    await flushPromises();
    return wrapper;
}

describe("HistoryDatasetDetails.vue", () => {
    it("should render details", async () => {
        const wrapper = await mountTarget({ datasetId: "datasetId", name: "history_dataset_peek" });
        expect(wrapper.text()).toBe("tabular_peek");
        await wrapper.setProps({ name: "history_dataset_name" });
        expect(wrapper.text()).toBe("tabular_name");
        await wrapper.setProps({ name: "history_dataset_info" });
        expect(wrapper.text()).toBe("tabular_misc_blurb");
        await wrapper.setProps({ name: "history_dataset_type" });
        expect(wrapper.text()).toBe("tabular");
    });

    it("shows the dataset name as text and renders the peek through v-sanitize-html", async () => {
        vi.mocked(sanitizeHtml).mockClear();
        const dataset = { ...tabularMetaData, name: "<b>name</b>", peek: "<table><tr><td>peek</td></tr></table>" };
        const wrapper = await mountTarget({ datasetId: "datasetId", name: "history_dataset_name" }, dataset);
        expect(wrapper.find("pre").text()).toBe("<b>name</b>");
        expect(wrapper.find("b").exists()).toBe(false);
        expect(sanitizeHtml).not.toHaveBeenCalled();

        await wrapper.setProps({ name: "history_dataset_peek" });
        expect(sanitizeHtml).toHaveBeenCalledWith(dataset.peek, "default");
        expect(wrapper.find("pre td").text()).toBe("peek");
    });
});
