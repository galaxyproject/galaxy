import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, nth, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import WorkflowSelectPreferredObjectStore from "./WorkflowSelectPreferredObjectStore.vue";
import WorkflowStorageConfiguration from "./WorkflowStorageConfiguration.vue";

const SELECTORS = {
    PRIMARY_STORAGE_BUTTON: ".workflow-storage-indicator-primary",
    INTERMEDIATE_STORAGE_BUTTON: ".workflow-storage-indicator-intermediate",
};

const localVue = getLocalVue(true);
enableAutoUnmount(afterEach);

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

    async function mountStorageConfiguration(splitObjectStore: boolean) {
        const pinia = createTestingPinia({ createSpy: vi.fn });
        const wrapper = mount(WorkflowStorageConfiguration, {
            props: {
                splitObjectStore,
                invocationPreferredObjectStoreId: null,
                invocationPreferredIntermediateObjectStoreId: null,
            },
            global: withPlugins(localVue, pinia),
            attachTo: document.body,
        });
        await flushPromises();
        return wrapper;
    }

    describe("rendering buttons", () => {
        it("shows primary and intermediate storage buttons when storage is split", async () => {
            const wrapper = await mountStorageConfiguration(true);
            const primaryEl = wrapper.find(SELECTORS.PRIMARY_STORAGE_BUTTON);
            expect(primaryEl.exists()).toBe(true);
            const intermediateEl = wrapper.find(SELECTORS.INTERMEDIATE_STORAGE_BUTTON);
            expect(intermediateEl.exists()).toBe(true);
        });

        it("shows only the primary storage button when storage is shared", async () => {
            const wrapper = await mountStorageConfiguration(false);
            const primaryEl = wrapper.find(SELECTORS.PRIMARY_STORAGE_BUTTON);
            expect(primaryEl.exists()).toBe(true);
            const intermediateEl = wrapper.find(SELECTORS.INTERMEDIATE_STORAGE_BUTTON);
            expect(intermediateEl.exists()).toBe(false);
        });
    });

    describe("event handling", () => {
        it("emits the selected primary storage ID with intermediate=false", async () => {
            const wrapper = await mountStorageConfiguration(true);

            const primaryButton = wrapper.get(SELECTORS.PRIMARY_STORAGE_BUTTON);
            await primaryButton.trigger("click");
            await flushPromises();

            const selectComponents = wrapper.findAllComponents(WorkflowSelectPreferredObjectStore);
            expect(selectComponents.length).toBeGreaterThan(0);
            nth(selectComponents, 0).vm.$emit("updated", "storage123");
            await flushPromises();

            expect(wrapper.emitted("updated")).toEqual([["storage123", false]]);
        });

        it("emits the selected intermediate storage ID with intermediate=true", async () => {
            const wrapper = await mountStorageConfiguration(true);

            const intermediateButton = wrapper.get(SELECTORS.INTERMEDIATE_STORAGE_BUTTON);
            await intermediateButton.trigger("click");
            await flushPromises();

            const selectComponents = wrapper.findAllComponents(WorkflowSelectPreferredObjectStore);
            expect(selectComponents.length).toBe(2);
            nth(selectComponents, 1).vm.$emit("updated", "storage123");
            await flushPromises();

            expect(wrapper.emitted("updated")).toEqual([["storage123", true]]);
        });
    });
});
