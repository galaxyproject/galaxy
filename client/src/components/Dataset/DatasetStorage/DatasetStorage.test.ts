import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import type { DatasetStorageDetails } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";

import DatasetStorage from "./DatasetStorage.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import DescribeObjectStore from "@/components/ObjectStore/DescribeObjectStore.vue";

enableAutoUnmount(afterEach);

const STORAGE_WITHOUT_ID: DatasetStorageDetails = {
    object_store_id: null,
    name: "Test name",
    description: "Test description",
    dataset_state: "ok",
    quota: { enabled: false, source: null },
    relocatable: false,
    shareable: false,
    badges: [],
    hashes: [],
    sources: [],
    percent_used: 0,
    private: false,
};
const DATASET_ID = "1";
const ERROR_MESSAGE = "Opps all errors.";

const { server, http } = useServerMock();

function createWrapper() {
    return shallowMount(DatasetStorage, {
        props: { datasetId: DATASET_ID },
        global: getLocalVue(),
    });
}

describe("DatasetStorage", () => {
    beforeEach(() => {
        server.use(
            http.get("/api/datasets/{dataset_id}/storage", ({ response }) => {
                return response(200).json(STORAGE_WITHOUT_ID);
            }),
        );
    });

    it("shows loading until storage details arrive", async () => {
        const wrapper = createWrapper();

        expect(wrapper.findAllComponents(LoadingSpan)).toHaveLength(1);
        expect(wrapper.findAllComponents(DescribeObjectStore)).toHaveLength(0);

        await flushPromises();

        expect(wrapper.findAllComponents(LoadingSpan)).toHaveLength(0);
        expect(wrapper.findAllComponents(DescribeObjectStore)).toHaveLength(1);
    });

    it("shows the API error and stops loading when fetching storage fails", async () => {
        server.use(
            http.get("/api/datasets/{dataset_id}/storage", ({ response }) => {
                return response("5XX").json({ err_msg: ERROR_MESSAGE, err_code: 500 }, { status: 500 });
            }),
        );
        const wrapper = createWrapper();

        await flushPromises();

        expect(wrapper.findAll(".error")).toHaveLength(1);
        expect(wrapper.find(".error").text()).toBe(ERROR_MESSAGE);
        expect(wrapper.findAllComponents(LoadingSpan)).toHaveLength(0);
    });

    it("describes storage even when the object store has no ID", async () => {
        const wrapper = createWrapper();

        await flushPromises();

        expect(wrapper.findAllComponents(LoadingSpan)).toHaveLength(0);
        expect(wrapper.findAllComponents(DescribeObjectStore)).toHaveLength(1);
        expect(wrapper.findComponent(DescribeObjectStore).props("storageInfo")).toEqual(STORAGE_WITHOUT_ID);
    });
});
