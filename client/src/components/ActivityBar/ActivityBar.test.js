import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import { dispatchEvent, getLocalVue, mockCurrentUserRequest, mockUnprivilegedToolsRequest } from "tests/jest/helpers";

import { useServerMock } from "@/api/client/__mocks__";
import { useConfig } from "@/composables/config";
import { useActivityStore } from "@/stores/activityStore";
import { useEventStore } from "@/stores/eventStore";

import mountTarget from "./ActivityBar.vue";

jest.mock("composables/config");
useConfig.mockReturnValue({
    config: {},
    isConfigLoaded: true,
});

jest.mock("vue-router", () => ({
    ...jest.requireActual("vue-router"),
    useRoute: jest.fn(() => ({})),
}));

const { server, http } = useServerMock();
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
        const pinia = createTestingPinia({ stubActions: false });
        const globalConfig = getLocalVue({ withPinia: false });

        activityStore = useActivityStore("default");
        eventStore = useEventStore();
        mockUnprivilegedToolsRequest(server, http);
        mockCurrentUserRequest(server, http);

        wrapper = mount(mountTarget, {
            global: {
                ...globalConfig.global,
                plugins: [...globalConfig.global.plugins, pinia],
                stubs: {
                    FontAwesomeIcon: true,
                },
            },
        });
    });

    it("rendering", async () => {
        activityStore.setAll([testActivity("1"), testActivity("2"), testActivity("3")]);
        await wrapper.vm.$nextTick();
        const items = wrapper.findAll("[aria-label='test-title']");
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
});
