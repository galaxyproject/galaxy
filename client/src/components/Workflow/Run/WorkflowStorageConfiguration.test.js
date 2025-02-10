import "tests/jest/mockHelpPopovers";

import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { findViaNavigation, getLocalVue } from "tests/jest/helpers";
import { ROOT_COMPONENT } from "utils/navigation";

import { useServerMock } from "@/api/client/__mocks__";

import WorkflowStorageConfiguration from "./WorkflowStorageConfiguration";

const localVue = getLocalVue(true);

const { server, http } = useServerMock();

jest.mock("@/components/Workflow/Run/WorkflowTargetPreferredObjectStorePopover.vue", () => ({
    name: "HelpPopover",
    render: (h) => h("div", "Mocked Popover"),
}));

describe("WorkflowStorageConfiguration.vue", () => {
    let wrapper;

    beforeEach(() => {
        server.use(
            http.get("/api/configuration", ({ response }) => {
                return response(200).json({});
            })
        );
    });

    async function doMount(split) {
        const propsData = {
            splitObjectStore: split,
            invocationPreferredObjectStoreId: null,
            invocationPreferredIntermediateObjectStoreId: null,
        };
        wrapper = mount(WorkflowStorageConfiguration, {
            propsData,
            localVue,
            pinia: createTestingPinia(),
        });
    }

    describe("rendering buttons", () => {
        it("should show two buttons on splitObjectStore", async () => {
            doMount(true);
            const primaryEl = findViaNavigation(wrapper, ROOT_COMPONENT.workflow_run.primary_storage_indciator);
            expect(primaryEl.exists()).toBeTruthy();
            const intermediateEl = findViaNavigation(
                wrapper,
                ROOT_COMPONENT.workflow_run.intermediate_storage_indciator
            );
            expect(intermediateEl.exists()).toBeTruthy();
            await flushPromises();
        });

        it("should show one button on not splitObjectStore", async () => {
            doMount(false);
            const primaryEl = findViaNavigation(wrapper, ROOT_COMPONENT.workflow_run.primary_storage_indciator);
            expect(primaryEl.exists()).toBeTruthy();
            const intermediateEl = findViaNavigation(
                wrapper,
                ROOT_COMPONENT.workflow_run.intermediate_storage_indciator
            );
            expect(intermediateEl.exists()).toBeFalsy();
            await flushPromises();
        });
    });

    describe("event handling", () => {
        it("should fire update events when primary selection is updated", async () => {
            doMount(true);
            await wrapper.vm.onUpdate("storage123");
            const emitted = wrapper.emitted();
            expect(emitted["updated"][0][0]).toEqual("storage123");
            expect(emitted["updated"][0][1]).toEqual(false);
            await flushPromises();
        });

        it("should fire an update event when intermediate selection is updated", async () => {
            doMount(true);
            await wrapper.vm.onUpdateIntermediate("storage123");
            const emitted = wrapper.emitted();
            expect(emitted["updated"][0][0]).toEqual("storage123");
            expect(emitted["updated"][0][1]).toEqual(true);
            await flushPromises();
        });
    });
});
