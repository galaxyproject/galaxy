import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { http as mswHttp, HttpResponse } from "msw";
import { setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

import { useServerMock } from "@/api/client/__mocks__";
import { testDatatypesMapper } from "@/components/Datatypes/test_fixtures";

import DatasetView from "./DatasetView.vue";

const { server, http } = useServerMock();

// Mock the datatypeVisualizationsStore
vi.mock("@/stores/datatypeVisualizationsStore", () => ({
    useDatatypeVisualizationsStore: vi.fn(() => ({
        getPreferredVisualizationForDatatype: vi.fn().mockImplementation((datatype) => {
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
enableAutoUnmount(afterEach);

const mockDataset = {
    id: DATASET_ID,
    name: "Test Dataset",
    state: "ok",
    file_ext: "txt",
    genome_build: "hg38",
    misc_blurb: "100 lines",
    misc_info: "Additional info",
    peek: "Needs a peek",
};

const errorDataset = { ...mockDataset, state: "error" };
const failedMetadataDataset = { ...mockDataset, state: "failed_metadata" };
const h5Dataset = { ...mockDataset, file_ext: "h5" };

function setupPinia(datasetStore) {
    const pinia = createTestingPinia({
        createSpy: vi.fn,
        initialState: {
            datasetStore: datasetStore,
            datatypeStore: {
                datatypeDetails: {
                    txt: {
                        id: "txt",
                        name: "Text",
                        display_type: "txt",
                    },
                },
            },
            datatypesMapperStore: {
                datatypesMapper: testDatatypesMapper,
            },
        },
        stubActions: false,
    });
    setActivePinia(pinia);
    return pinia;
}

async function mountDatasetView(tab = "preview", { dataset = mockDataset } = {}) {
    const datasetStore = {
        storedDatasets: dataset ? { [DATASET_ID]: { ...dataset } } : {},
    };
    const pinia = setupPinia(datasetStore);

    const router = createRouter({ history: createMemoryHistory(), routes: [] });
    router.push = vi.fn();
    router.replace = vi.fn();

    const wrapper = mount(DatasetView, {
        props: {
            datasetId: DATASET_ID,
            tab: tab,
        },
        global: withPlugins(getLocalVue(), pinia, router),
        attachTo: document.createElement("div"),
        stubs: {
            // Only shallow stub certain components
            FontAwesomeIcon: true,
            Heading: {
                template: "<div><slot></slot></div>",
                props: ["h1", "separator"],
            },
            BLink: {
                template: '<a :href="to"><slot></slot></a>',
                props: ["to"],
            },
            BNavItem: {
                name: "BNavItem",
                template: '<li><a :href="to"><slot></slot></a></li>',
                props: ["to", "active"],
            },
            GTabs: {
                template: '<div class="tabs-container"><slot></slot></div>',
                props: ["pills", "card", "lazy", "value"],
            },
            GTab: {
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

describe("DatasetView", () => {
    beforeEach(() => {
        class IO {
            constructor() {}
            observe() {}
            unobserve() {}
            disconnect() {}
        }
        vi.stubGlobal("IntersectionObserver", IO);
        vi.stubGlobal("MutationObserver", IO);
        vi.stubGlobal(
            "URL",
            class extends URL {
                static createObjectURL = vi.fn(() => "blob:http://localhost/test-preview");
                static revokeObjectURL = vi.fn();
            },
        );
        server.use(
            http.get("/api/configuration", ({ response }) => response.untyped(HttpResponse.json({}))),
            http.get("/api/plugins", ({ response }) => response(200).json([])),
            mswHttp.get("http://localhost/datasets/:dataset_id/display/", ({ request }) => {
                expect(request.url).toContain("preview=True");
                return HttpResponse.text("preview data", {
                    status: 200,
                    headers: {
                        "content-type": "text/plain",
                    },
                });
            }),
            http.get("/api/datatypes/{datatype}", ({ response }) => response.untyped(HttpResponse.json({}))),
        );
    });

    afterEach(() => {
        vi.unstubAllGlobals();
    });

    describe("Component mounting and basic functionality", () => {
        it.each(["preview", "raw"])("uses the download endpoint from the %s tab", async (tab) => {
            server.use(
                http.get("/api/datatypes/:datatype_id", ({ response }) =>
                    response(200).json({
                        id: "mp4",
                        display_behavior: "download",
                    }),
                ),
            );
            const wrapper = await mountDatasetView(tab, {
                dataset: { ...mockDataset, name: "Annotated video", file_ext: "mp4" },
            });

            const downloadLink = wrapper.get(".auto-download-message a");
            expect(downloadLink.text()).toContain("Download File");
            expect(downloadLink.attributes("href")).toBe(`/api/datasets/${DATASET_ID}/download`);
        });

        it("mounts with correct props", async () => {
            const wrapper = await mountDatasetView();
            expect(wrapper.exists()).toBe(true);
            expect(wrapper.props().datasetId).toBe(DATASET_ID);
            expect(wrapper.props().tab).toBe("preview");
        });

        it("shows loading message when dataset is loading", async () => {
            server.use(http.get("/api/datasets/{dataset_id}", () => new Promise(() => {})));
            const wrapper = await mountDatasetView("preview", { dataset: null });
            expect(wrapper.find(".loading-message").exists()).toBe(true);
            expect(wrapper.find(".loading-message").text()).toBe("Loading dataset details...");
            expect(wrapper.find(".dataset-view").exists()).toBe(false);
        });

        it("renders dataset information", async () => {
            const wrapper = await mountDatasetView();

            expect(wrapper.vm.$props.datasetId).toBe(DATASET_ID);
            expect(wrapper.vm.$props.tab).toBe("preview");

            const datasetStore = wrapper.vm.$pinia.state.value.datasetStore;
            expect(datasetStore.storedDatasets[DATASET_ID]).toBeDefined();
            expect(datasetStore.storedDatasets[DATASET_ID].name).toBe("Test Dataset");
            expect(wrapper.get(".dataset-name").text()).toBe("Test Dataset");
        });
    });

    describe("Tab navigation functionality", () => {
        it.each([
            { tab: "details", child: "DatasetDetails", dataset: mockDataset },
            { tab: "visualize", child: "VisualizationsList", dataset: mockDataset },
            { tab: "edit", child: "DatasetAttributes", dataset: mockDataset },
            { tab: "error", child: "DatasetError", dataset: errorDataset },
        ])("renders the $tab tab and its $child child", async ({ tab, child, dataset }) => {
            const wrapper = await mountDatasetView(tab, { dataset });

            expect(wrapper.props().tab).toBe(tab);
            expect(wrapper.getComponent({ name: child }).props("datasetId")).toBe(DATASET_ID);
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
        it.each([
            { state: "error", dataset: errorDataset },
            { state: "failed_metadata", dataset: failedMetadataDataset },
        ])("keeps the error tab without redirecting for $state datasets", async ({ dataset }) => {
            const wrapper = await mountDatasetView("error", { dataset });

            expect(wrapper.vm.$router.replace).not.toHaveBeenCalled();
            expect(wrapper.props().tab).toBe("error");
            expect(wrapper.getComponent({ name: "DatasetError" }).props("datasetId")).toBe(DATASET_ID);
        });

        it.each(["upload", "running", "paused"])("mounts the preview tab for a %s dataset", async (state) => {
            const wrapper = await mountDatasetView("preview", { dataset: { ...mockDataset, state } });

            expect(wrapper.exists()).toBe(true);
            expect(wrapper.props().datasetId).toBe(DATASET_ID);
            expect(wrapper.props().tab).toBe("preview");
        });

        it.skip("uses preferred visualization for supported datatypes", async () => {
            const wrapper = await mountDatasetView("preview", { dataset: h5Dataset });

            // Check that the preferredVisualization was set
            expect(wrapper.vm.preferredVisualization).toBe("h5web");

            // Check that we're using the VisualizationFrame for the preferred visualization
            expect(wrapper.findComponent({ name: "VisualizationFrame" }).exists()).toBe(true);
            expect(wrapper.find("iframe").exists()).toBe(false);
        });

        it("falls back to default preview for unsupported datatypes", async () => {
            const wrapper = await mountDatasetView("preview");

            // No preferred visualization should be set. `getPreferredVisualization` falls
            // back to `null` (not `undefined`) when nothing is configured.
            expect(wrapper.vm.preferredVisualization).toBeNull();

            // Check that we're using the default iframe
            expect(wrapper.findComponent({ name: "VisualizationFrame" }).exists()).toBe(false);
            expect(wrapper.find("iframe").exists()).toBe(true);
            expect(wrapper.find("iframe").attributes("src")).toBe("blob:http://localhost/test-preview");
        });
    });

    describe("URL and routing", () => {
        it("tests navigation behavior", async () => {
            const wrapper = await mountDatasetView("preview");

            await wrapper.setProps({ tab: "details" });
            await flushPromises();

            expect(wrapper.vm.$props.tab).toBe("details");
        });

        it.each([
            { label: "Preview", dataset: mockDataset, path: `/datasets/${DATASET_ID}/preview` },
            { label: "Details", dataset: mockDataset, path: `/datasets/${DATASET_ID}/details` },
            { label: "Visualize", dataset: mockDataset, path: `/datasets/${DATASET_ID}/visualize` },
            { label: "Edit", dataset: mockDataset, path: `/datasets/${DATASET_ID}/edit` },
            { label: "Error", dataset: errorDataset, path: `/datasets/${DATASET_ID}/error` },
        ])("links the $label tab to $path", async ({ label, dataset, path }) => {
            const wrapper = await mountDatasetView("preview", { dataset });
            const navigationItem = wrapper
                .findAllComponents({ name: "BNavItem" })
                .find((item) => item.text() === label);

            expect(navigationItem).toBeDefined();
            expect(navigationItem.find("a").attributes("href")).toBe(path);
        });
    });

    describe("File size", () => {
        it("shows the formatted size as text", async () => {
            const wrapper = await mountDatasetView("preview", { dataset: { ...mockDataset, file_size: 2048 } });
            const size = wrapper.find(".filesize .value");
            expect(size.text()).toBe("2 KB");
            expect(size.find("strong").exists()).toBe(false);
        });
    });
});
