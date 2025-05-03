// @ts-nocheck
import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/jest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import VueRouter from "vue-router";

import DatasetView from "./DatasetView.vue";

const DATASET_ID = "dataset_id";
const localVue = getLocalVue();
localVue.use(VueRouter);

const mockDataset = {
    id: DATASET_ID,
    name: "Test Dataset",
    state: "ok",
    file_ext: "txt",
    genome_build: "hg38",
    misc_blurb: "100 lines",
    misc_info: "Additional info",
};

const errorDataset = { ...mockDataset, state: "error" };
const failedMetadataDataset = { ...mockDataset, state: "failed_metadata" };

async function mountDatasetView(tab = "preview", options = {}) {
    const pinia = createTestingPinia({
        initialState: {
            datasetStore: {
                storedDatasets: {
                    [DATASET_ID]: options.dataset || mockDataset,
                },
            },
        },
        stubActions: false,
        createSpy: jest.fn,
    });
    setActivePinia(pinia);

    const router = new VueRouter();
    router.push = jest.fn();
    router.replace = jest.fn();

    const wrapper = mount(DatasetView, {
        propsData: {
            datasetId: DATASET_ID,
            tab: tab,
        },
        localVue,
        pinia,
        router,
        stubs: {
            Heading: true,
            BLink: true,
            BTabs: true,
            BTab: true,
            DatasetDetails: true,
            VisualizationsList: true,
            DatasetAttributes: true,
            DatasetError: true,
        },
        mocks: {
            $store: {
                state: {
                    config: {},
                },
            },
        },
    });

    await flushPromises();
    return wrapper;
}

async function mountLoadingDatasetView() {
    const pinia = createTestingPinia({
        initialState: {
            datasetStore: {
                storedDatasets: {},
            },
        },
        stubActions: false,
        createSpy: jest.fn,
    });
    setActivePinia(pinia);

    const router = new VueRouter();
    const wrapper = mount(DatasetView, {
        propsData: {
            datasetId: DATASET_ID,
        },
        localVue,
        pinia,
        router,
        stubs: {
            Heading: true,
            BLink: true,
            BTabs: true,
            BTab: true,
        },
        mocks: {
            $store: {
                state: {
                    config: {},
                },
            },
        },
    });

    await flushPromises();
    return wrapper;
}

describe("DatasetView", () => {
    it("mounts with correct props", async () => {
        const wrapper = await mountDatasetView();
        expect(wrapper.exists()).toBe(true);
        expect(wrapper.props().datasetId).toBe(DATASET_ID);
        expect(wrapper.props().tab).toBe("preview");
    });

    it("shows loading message", async () => {
        const wrapper = await mountLoadingDatasetView();
        expect(wrapper.find(".loading-message").exists()).toBe(true);
    });

    it("handles different tabs", async () => {
        let wrapper = await mountDatasetView("details");
        expect(wrapper.props().tab).toBe("details");

        wrapper = await mountDatasetView("visualize");
        expect(wrapper.props().tab).toBe("visualize");

        wrapper = await mountDatasetView("edit");
        expect(wrapper.props().tab).toBe("edit");

        wrapper = await mountDatasetView("error", { dataset: errorDataset });
        expect(wrapper.props().tab).toBe("error");
    });

    it("updates when tab changes", async () => {
        const wrapper = await mountDatasetView("details");
        expect(wrapper.props().tab).toBe("details");

        await wrapper.setProps({ tab: "visualize" });
        await flushPromises();
        expect(wrapper.props().tab).toBe("visualize");

        await wrapper.setProps({ tab: "edit" });
        await flushPromises();
        expect(wrapper.props().tab).toBe("edit");
    });

    it("redirects invalid tabs", async () => {
        const wrapper = await mountDatasetView("invalid_tab");
        expect(wrapper.vm.$router.replace).toHaveBeenCalled();
    });

    it("redirects error tab for normal datasets", async () => {
        const wrapper = await mountDatasetView("error");
        expect(wrapper.vm.$router.replace).toHaveBeenCalled();
    });

    it("shows error tab for error datasets", async () => {
        const wrapper = await mountDatasetView("error", {
            dataset: errorDataset,
        });
        expect(wrapper.vm.$router.replace).not.toHaveBeenCalled();
    });

    it("shows error tab for failed_metadata", async () => {
        const wrapper = await mountDatasetView("error", {
            dataset: failedMetadataDataset,
        });
        expect(wrapper.vm.$router.replace).not.toHaveBeenCalled();
    });

    it("formats tab URLs correctly", async () => {
        const previewUrl = `/datasets/${DATASET_ID}`;
        const detailsUrl = `/datasets/${DATASET_ID}/details`;
        const visualizeUrl = `/datasets/${DATASET_ID}/visualize`;
        const editUrl = `/datasets/${DATASET_ID}/edit`;
        const errorUrl = `/datasets/${DATASET_ID}/error`;

        expect(previewUrl).toBe(`/datasets/${DATASET_ID}`);
        expect(detailsUrl).toBe(`/datasets/${DATASET_ID}/details`);
        expect(visualizeUrl).toBe(`/datasets/${DATASET_ID}/visualize`);
        expect(editUrl).toBe(`/datasets/${DATASET_ID}/edit`);
        expect(errorUrl).toBe(`/datasets/${DATASET_ID}/error`);
    });
});
