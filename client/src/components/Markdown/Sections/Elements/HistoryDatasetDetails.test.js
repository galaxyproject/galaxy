import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";

import { useServerMock } from "@/api/client/__mocks__";
import { testDatatypesMapper } from "@/components/Datatypes/test_fixtures";
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
    const pinia = createTestingPinia({ stubActions: false });
    const datatypesStore = useDatatypesMapperStore();
    datatypesStore.datatypesMapper = testDatatypesMapper;
    return pinia;
}

async function mountTarget(propsData = {}) {
    server.use(http.get("/api/datasets/{dataset_id}", ({ response }) => response(200).json(tabularMetaData)));
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
});
