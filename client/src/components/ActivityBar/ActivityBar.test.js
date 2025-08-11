import { createTestingPinia } from "@pinia/testing";
import { dispatchEvent, getLocalVue, mockUnprivilegedToolsRequest } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import { PiniaVuePlugin } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { useServerMock } from "@/api/client/__mocks__";
import { useActivityStore } from "@/stores/activityStore";
import { useEventStore } from "@/stores/eventStore";

import mountTarget from "./ActivityBar.vue";

const mockConfig = ref({});

vi.mock("@/composables/config", () => ({
    useConfig: vi.fn(() => ({
        config: mockConfig,
        isConfigLoaded: true,
    })),
}));

vi.mock("vue-router", () => ({
    useRoute: vi.fn(() => ({})),
}));

const { server, http } = useServerMock();

const localVue = getLocalVue();
localVue.use(PiniaVuePlugin);

function testActivity(id, newOptions = {}) {
    const defaultOptions = {
        anonymous: true,
        id: `test-${id}`,
        description: "test-description",
        icon: "test-icon",
        mutable: true,
        optional: false,
        title: "test-title",
        to: "test-to",
        tooltip: "test-tooltip",
        visible: true,
    };
    return { ...defaultOptions, ...newOptions };
}

describe("ActivityBar", () => {
    let activityStore;
    let eventStore;
    let wrapper;

    beforeEach(async () => {
        mockConfig.value = {};
        const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
        activityStore = useActivityStore("default");
        eventStore = useEventStore();
        mockUnprivilegedToolsRequest(server, http);
        server.use(
            http.get("/api/configuration", ({ response }) => {
                return response(200).json({});
            }),
        );
        wrapper = shallowMount(mountTarget, {
            localVue,
            pinia,
        });
    });

    it("rendering", async () => {
        activityStore.setAll([testActivity("1"), testActivity("2"), testActivity("3")]);
        await wrapper.vm.$nextTick();
        const items = wrapper.findAll("[title='test-title']");
        expect(items.length).toBe(3);
    });

    it("drag start", async () => {
        activityStore.setAll([testActivity("1"), testActivity("2"), testActivity("3")]);
        eventStore.setDragData({
            id: "workflow-id",
            description: "workflow-description",
            model_class: "StoredWorkflow",
            name: "workflow-name",
        });
        const bar = wrapper.find("[data-description='activity bar']");
        dispatchEvent(bar, "dragenter");
        const emittedEvent = wrapper.emitted()["dragstart"][0][0];
        expect(emittedEvent.to).toBe("/workflows/run?id=workflow-id");
    });

    describe("interactivetools visibility", () => {
        async function mountWithInteractiveToolsConfig(enabled, activityBarId) {
            mockConfig.value = { interactivetools_enable: enabled };
            const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
            const testStore = useActivityStore(activityBarId);
            testStore.setAll([
                testActivity("1"),
                testActivity("interactivetools", { id: "interactivetools", title: "Interactive Tools" }),
                testActivity("3"),
            ]);
            mockUnprivilegedToolsRequest(server, http);
            const testWrapper = shallowMount(mountTarget, {
                localVue,
                pinia,
                propsData: { activityBarId },
            });
            await testWrapper.vm.$nextTick();
            return testWrapper;
        }

        it("hides interactivetools activity when interactivetools_enable is false", async () => {
            const testWrapper = await mountWithInteractiveToolsConfig(false, "it-test-hide");
            expect(testWrapper.findAll("[id='interactivetools']").length).toBe(0);
        });

        it("shows interactivetools activity when interactivetools_enable is true", async () => {
            const testWrapper = await mountWithInteractiveToolsConfig(true, "it-test-show");
            expect(testWrapper.findAll("[id='interactivetools']").length).toBe(1);
        });
    });
});
