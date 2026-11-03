import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { computed } from "vue";

import type { PathDestination } from "@/composables/datasetPathDestination";
import * as datasetPathDestinationModule from "@/composables/datasetPathDestination";

import DatasetIndex from "./DatasetIndex.vue";

const localVue = getLocalVue();

vi.mock("@/composables/datasetPathDestination");

describe("DatasetIndex", () => {
    type DatasetPathDestination = ReturnType<
        typeof datasetPathDestinationModule.useDatasetPathDestination
    >["datasetPathDestination"]["value"];
    const mockDatasetPathDestination = vi.fn<DatasetPathDestination>();

    beforeEach(() => {
        mockDatasetPathDestination.mockReset();
        vi.mocked(datasetPathDestinationModule.useDatasetPathDestination).mockImplementation(() => ({
            datasetPathDestination: computed(() => mockDatasetPathDestination),
        }));
    });

    afterEach(() => {
        vi.mocked(datasetPathDestinationModule.useDatasetPathDestination).mockReset();
        mockDatasetPathDestination.mockReset();
    });
    enableAutoUnmount(afterEach);

    it("renders GTable when dataset has valid content", async () => {
        const mockPathDestination: PathDestination = {
            datasetContent: [
                { path: "file1.txt", class: "File" },
                { path: "file2.csv", class: "File" },
            ],
            isDirectory: false,
        };

        mockDatasetPathDestination.mockResolvedValue(mockPathDestination);

        const wrapper = shallowMount(DatasetIndex, {
            props: {
                historyDatasetId: "test-dataset-123",
            },
            global: localVue,
        });

        // Wait for async computedAsync to resolve
        await flushPromises();

        const gTable = wrapper.findComponent({ name: "GTable" });
        expect(gTable.exists()).toBe(true);
        expect(gTable.attributes("fields")).toBeDefined();
    });

    it("displays error message when dataset is not composite", async () => {
        mockDatasetPathDestination.mockResolvedValue(null);

        const wrapper = shallowMount(DatasetIndex, {
            props: {
                historyDatasetId: "test-dataset-123",
            },
            global: localVue,
        });

        await flushPromises();

        expect(wrapper.text()).toContain("Dataset is not composite!");
        const gTable = wrapper.findComponent({ name: "GTable" });
        expect(gTable.exists()).toBe(false);
    });

    it("displays error message when path points to a file", async () => {
        const mockPathDestination: PathDestination = {
            datasetContent: [{ path: "file1.txt", class: "File" }],
            isDirectory: false,
            fileLink: "/api/datasets/123/file1.txt",
        };

        mockDatasetPathDestination.mockResolvedValue(mockPathDestination);

        const wrapper = shallowMount(DatasetIndex, {
            props: {
                historyDatasetId: "test-dataset-123",
                path: "file1.txt",
            },
            global: localVue,
        });

        await flushPromises();

        expect(wrapper.text()).toContain("is not a directory!");
        const gTable = wrapper.findComponent({ name: "GTable" });
        expect(gTable.exists()).toBe(false);
    });

    it("displays error message when path is not found", async () => {
        const mockPathDestination: PathDestination = {
            datasetContent: [{ path: "other.txt", class: "File" }],
            isDirectory: false,
            filepath: "nonexistent.txt",
        };

        mockDatasetPathDestination.mockResolvedValue(mockPathDestination);

        const wrapper = shallowMount(DatasetIndex, {
            props: {
                historyDatasetId: "test-dataset-123",
                path: "nonexistent.txt",
            },
            global: localVue,
        });

        await flushPromises();

        expect(wrapper.text()).toContain("nonexistent.txt");
        expect(wrapper.text()).toContain("is not found!");
        const gTable = wrapper.findComponent({ name: "GTable" });
        expect(gTable.exists()).toBe(false);
    });

    it("renders GTable with correct fields configuration", async () => {
        const mockPathDestination: PathDestination = {
            datasetContent: [
                { path: "test.txt", class: "File" },
                { path: "data.csv", class: "File" },
            ],
            isDirectory: false,
        };

        mockDatasetPathDestination.mockResolvedValue(mockPathDestination);

        const wrapper = shallowMount(DatasetIndex, {
            props: {
                historyDatasetId: "test-dataset-123",
            },
            global: localVue,
        });

        await flushPromises();

        const html = wrapper.html();
        expect(html).toContain("fields");
        expect(html).toContain("items");
        expect(html).toContain("[object Object]");
        expect(wrapper.getComponent({ name: "GTable" }).props("fields")).toEqual([
            { key: "path", label: "Path", sortable: true },
            { key: "class", label: "Type", sortable: true },
        ]);
    });

    it("filters directory content when viewing a subdirectory", async () => {
        const mockPathDestination: PathDestination = {
            datasetContent: [
                { path: "subfolder/nested.txt", class: "File" },
                { path: "subfolder/another.csv", class: "File" },
            ],
            isDirectory: true,
            filepath: "subfolder",
        };

        mockDatasetPathDestination.mockResolvedValue(mockPathDestination);

        const wrapper = shallowMount(DatasetIndex, {
            props: {
                historyDatasetId: "test-dataset-123",
                path: "subfolder",
            },
            global: localVue,
        });

        await flushPromises();

        expect(wrapper.html()).toContain("fields");
        expect(wrapper.html()).not.toContain("is not found");
        expect(wrapper.html()).not.toContain("is not a directory");
        expect(wrapper.getComponent({ name: "GTable" }).props("items")).toEqual([
            { path: "nested.txt", class: "File" },
            { path: "another.csv", class: "File" },
        ]);
    });

    it("does not render GTable when error message is displayed", async () => {
        mockDatasetPathDestination.mockResolvedValue(null);

        const wrapper = shallowMount(DatasetIndex, {
            props: {
                historyDatasetId: "test-dataset-123",
            },
            global: localVue,
        });

        await flushPromises();

        const gTable = wrapper.findComponent({ name: "GTable" });
        const errorDiv = wrapper.find("div");

        expect(gTable.exists()).toBe(false);
        expect(errorDiv.exists()).toBe(true);
        expect(errorDiv.text()).toContain("Dataset is not composite!");
    });
});
