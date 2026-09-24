import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import WorkflowSelectPreferredObjectStore from "./WorkflowSelectPreferredObjectStore.vue";
import WorkflowStorageConfiguration from "./WorkflowStorageConfiguration.vue";

const SELECTORS = {
    PRIMARY_STORAGE_BUTTON: ".workflow-storage-indicator-primary",
    INTERMEDIATE_STORAGE_BUTTON: ".workflow-storage-indicator-intermediate",
};

const localVue = getLocalVue(true);

const { server, http } = useServerMock();

describe("WorkflowStorageConfiguration.vue", () => {
    beforeEach(() => {
        server.use(
            http.get("/api/configuration", ({ response }) => {
                return response(200).json({});
            }),
            http.get("/api/object_stores", ({ response }) => {
                return response(200).json([]);
            }),
        );
    });

    function doMount(split: boolean): Wrapper<Vue> {
        const wrapper = mount(WorkflowStorageConfiguration as object, {
            propsData: {
                splitObjectStore: split,
                invocationPreferredObjectStoreId: null,
                invocationPreferredIntermediateObjectStoreId: null,
            },
            localVue,
            pinia: createTestingPinia({ createSpy: vi.fn }),
            attachTo: document.body,
        });
        return wrapper;
    }

    describe("rendering buttons", () => {
        it("should show two buttons on splitObjectStore", async () => {
            const wrapper = doMount(true);
            const primaryEl = wrapper.find(SELECTORS.PRIMARY_STORAGE_BUTTON);
            expect(primaryEl.exists()).toBeTruthy();
            const intermediateEl = wrapper.find(SELECTORS.INTERMEDIATE_STORAGE_BUTTON);
            expect(intermediateEl.exists()).toBeTruthy();
            await flushPromises();
        });

        it("should show one button on not splitObjectStore", async () => {
            const wrapper = doMount(false);
            const primaryEl = wrapper.find(SELECTORS.PRIMARY_STORAGE_BUTTON);
            expect(primaryEl.exists()).toBeTruthy();
            const intermediateEl = wrapper.find(SELECTORS.INTERMEDIATE_STORAGE_BUTTON);
            expect(intermediateEl.exists()).toBeFalsy();
            await flushPromises();
        });
    });

    describe("event handling", () => {
        it("should fire update events when primary selection is updated", async () => {
            const wrapper = doMount(true);
            await flushPromises();

            // Click the primary storage button to open the modal
            const primaryButton = wrapper.find(SELECTORS.PRIMARY_STORAGE_BUTTON);
            await primaryButton.trigger("click");
            await flushPromises();

            // Find the first WorkflowSelectPreferredObjectStore component and emit its updated event
            const selectComponents = wrapper.findAllComponents(WorkflowSelectPreferredObjectStore);
            expect(selectComponents.length).toBeGreaterThan(0);
            selectComponents.at(0).vm.$emit("updated", "storage123");
            await flushPromises();

            const emitted = wrapper.emitted();
            expect(emitted["updated"]?.[0]?.[0]).toEqual("storage123");
            expect(emitted["updated"]?.[0]?.[1]).toEqual(false);
        });

        it("should fire an update event when intermediate selection is updated", async () => {
            const wrapper = doMount(true);
            await flushPromises();

            // Click the intermediate storage button to open the modal
            const intermediateButton = wrapper.find(SELECTORS.INTERMEDIATE_STORAGE_BUTTON);
            await intermediateButton.trigger("click");
            await flushPromises();

            // Find the WorkflowSelectPreferredObjectStore components (there are 2, we want the 2nd one for intermediate)
            const selectComponents = wrapper.findAllComponents(WorkflowSelectPreferredObjectStore);
            expect(selectComponents.length).toBe(2);
            selectComponents.at(1).vm.$emit("updated", "storage123");
            await flushPromises();

            const emitted = wrapper.emitted();
            expect(emitted["updated"]?.[0]?.[0]).toEqual("storage123");
            expect(emitted["updated"]?.[0]?.[1]).toEqual(true);
        });
    });
});
