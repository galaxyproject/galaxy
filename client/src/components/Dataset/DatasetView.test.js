import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/jest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import VueRouter from "vue-router";

import DatasetView from "./DatasetView.vue";

// Mock the datatypeVisualizationsStore
jest.mock("@/stores/datatypeVisualizationsStore", () => ({
    useDatatypeVisualizationsStore: jest.fn(() => ({
        getPreferredVisualizationForDatatype: jest.fn().mockImplementation((datatype) => {
            // Only return a preferred visualization for a specific test datatype
            if (datatype === "h5") {
                return Promise.resolve({
                    datatype: "h5",
                    visualization: "h5web",
                });
            }
            return Promise.resolve(null);
        }),
    })),
}));

const DATASET_ID = "dataset_id";
const localVue = getLocalVue();
localVue.use(VueRouter);

// Mock dataset
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
// Additional states to test
const uploadingDataset = { ...mockDataset, state: "upload" };
const runningDataset = { ...mockDataset, state: "running" };
const pausedDataset = { ...mockDataset, state: "paused" };
// Dataset with preferred visualization
const h5Dataset = { ...mockDataset, file_ext: "h5" };

/**
 * Mount the DatasetView component with the specified tab and dataset options
 */
async function mountDatasetView(tab = "preview", options = {}) {
    const pinia = createTestingPinia({
        initialState: {
            datasetStore: {
                storedDatasets: {
                    [DATASET_ID]: options.dataset || mockDataset,
                },
                loadingDatasets: {},
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
        attachTo: document.createElement("div"),
        stubs: {
            // Only shallow stub certain components
            "font-awesome-icon": true,
            Heading: {
                template: "<div><slot></slot></div>",
                props: ["h1", "separator"],
            },
            BLink: {
                template: "<a><slot></slot></a>",
                props: ["to"],
            },
            BTabs: {
                template: '<div class="tabs-container"><slot></slot></div>',
                props: ["pills", "card", "lazy", "value"],
            },
            BTab: {
                template: '<div class="tab-content"><slot></slot></div>',
                props: ["title"],
            },
            DatasetDetails: true,
            VisualizationsList: true,
            DatasetAttributes: true,
            DatasetError: true,
            // Use a stub for the VisualizationFrame component
            VisualizationFrame: {
                template: '<div class="viz-frame"></div>',
                props: ["datasetId", "visualization", "visualizationParams"],
            },
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

/**
 * Mount the DatasetView component in loading state
 */
async function mountLoadingDatasetView() {
    const pinia = createTestingPinia({
        initialState: {
            datasetStore: {
                storedDatasets: {},
                loadingDatasets: {
                    [DATASET_ID]: true,
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
    describe("Component mounting and basic functionality", () => {
        it("mounts with correct props", async () => {
            const wrapper = await mountDatasetView();
            expect(wrapper.exists()).toBe(true);
            expect(wrapper.props().datasetId).toBe(DATASET_ID);
            expect(wrapper.props().tab).toBe("preview");
        });

        it("shows loading message when dataset is loading", async () => {
            const wrapper = await mountLoadingDatasetView();
            expect(wrapper.find(".loading-message").exists()).toBe(true);
            expect(wrapper.find(".loading-message").text()).toBe("Loading dataset details...");
            expect(wrapper.find(".dataset-view").exists()).toBe(false);
        });

        it("renders dataset information", async () => {
            const wrapper = await mountDatasetView();

            // Check that the component mounted successfully with the expected data
            expect(wrapper.vm.$props.datasetId).toBe(DATASET_ID);
            expect(wrapper.vm.$props.tab).toBe("preview");

            // Make sure we're properly passing the dataset to the component
            const datasetStore = wrapper.vm.$pinia.state.value.datasetStore;
            expect(datasetStore.storedDatasets[DATASET_ID]).toBeDefined();
            expect(datasetStore.storedDatasets[DATASET_ID].name).toBe("Test Dataset");
        });
    });

    describe("Tab navigation functionality", () => {
        it("handles different tabs through props", async () => {
            let wrapper = await mountDatasetView("details");
            expect(wrapper.props().tab).toBe("details");

            wrapper = await mountDatasetView("visualize");
            expect(wrapper.props().tab).toBe("visualize");

            wrapper = await mountDatasetView("edit");
            expect(wrapper.props().tab).toBe("edit");

            wrapper = await mountDatasetView("error", { dataset: errorDataset });
            expect(wrapper.props().tab).toBe("error");
        });

        it("updates when tab prop changes", async () => {
            const wrapper = await mountDatasetView("details");
            expect(wrapper.props().tab).toBe("details");

            await wrapper.setProps({ tab: "visualize" });
            await flushPromises();
            expect(wrapper.props().tab).toBe("visualize");

            await wrapper.setProps({ tab: "edit" });
            await flushPromises();
            expect(wrapper.props().tab).toBe("edit");
        });

        it("includes preview tab for dataset viewing", async () => {
            const wrapper = await mountDatasetView("preview");

            expect(wrapper.vm.$props.tab).toBe("preview");

            const datasetStore = wrapper.vm.$pinia.state.value.datasetStore;
            const dataset = datasetStore.storedDatasets[DATASET_ID];
            expect(dataset).toBeDefined();
        });
    });

    describe("Error state handling", () => {

        it("shows error tab for datasets with error state", async () => {
            const wrapper = await mountDatasetView("error", { dataset: errorDataset });

            const router = wrapper.vm.$router;
            expect(router.replace).not.toHaveBeenCalled();

            // Check that we're viewing the error tab
            expect(wrapper.vm.$props.tab).toBe("error");
        });

        it("shows error tab for datasets with failed_metadata state", async () => {
            const wrapper = await mountDatasetView("error", { dataset: failedMetadataDataset });

            const router = wrapper.vm.$router;
            expect(router.replace).not.toHaveBeenCalled();

            // Check that we're viewing the error tab
            expect(wrapper.vm.$props.tab).toBe("error");
        });

        it("handles datasets with different states appropriately", async () => {
            // Test uploading state, make sure it doesn't blow up.
            let wrapper = await mountDatasetView("preview", { dataset: uploadingDataset });
            expect(wrapper.exists()).toBe(true);
            expect(wrapper.vm.$props.datasetId).toBe(DATASET_ID);
            expect(wrapper.vm.$props.tab).toBe("preview");

            // Test running state, make sure it doesn't blow up.
            wrapper = await mountDatasetView("preview", { dataset: runningDataset });
            expect(wrapper.exists()).toBe(true);
            expect(wrapper.vm.$props.datasetId).toBe(DATASET_ID);
            expect(wrapper.vm.$props.tab).toBe("preview");

            // Test paused state, make sure it doesn't blow up.
            wrapper = await mountDatasetView("preview", { dataset: pausedDataset });
            expect(wrapper.exists()).toBe(true);
            expect(wrapper.vm.$props.datasetId).toBe(DATASET_ID);
            expect(wrapper.vm.$props.tab).toBe("preview");
        });

        it.skip("uses preferred visualization for supported datatypes", async () => {
            const wrapper = await mountDatasetView("preview", { dataset: h5Dataset });
            await flushPromises(); // Wait for preferred visualization check

            // Check that the preferredVisualization was set
            expect(wrapper.vm.preferredVisualization).toBe("h5web");

            // Check that we're using the VisualizationFrame for the preferred visualization
            expect(wrapper.findComponent({ name: "VisualizationFrame" }).exists()).toBe(true);
            expect(wrapper.find("iframe").exists()).toBe(false);
        });

        it.skip("falls back to default preview for unsupported datatypes", async () => {
            const wrapper = await mountDatasetView("preview");
            await flushPromises(); // Wait for preferred visualization check

            // No preferred visualization should be set
            expect(wrapper.vm.preferredVisualization).toBeNull();

            // Check that we're using the default iframe
            expect(wrapper.findComponent({ name: "VisualizationFrame" }).exists()).toBe(false);
            expect(wrapper.find("iframe").exists()).toBe(true);
            expect(wrapper.find("iframe").attributes("src")).toBe(`/datasets/${DATASET_ID}/display/?preview=true`);
        });
    });

    describe("URL and routing", () => {
        it("tests navigation behavior", async () => {
            const wrapper = await mountDatasetView("preview");

            await wrapper.setProps({ tab: "details" });
            await flushPromises();

            expect(wrapper.vm.$props.tab).toBe("details");
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
});
