import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import { findViaNavigation, getLocalVue } from "tests/jest/helpers";
import { ROOT_COMPONENT } from "utils/navigation";

import WorkflowStorageConfiguration from "./WorkflowStorageConfiguration";

const localVue = getLocalVue(true);

describe("WorkflowStorageConfiguration.vue", () => {
    let wrapper;

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
        });
    });

    describe("event handling", () => {
        it("should fire update events when primary selection is updated", async () => {
            doMount(true);
            await wrapper.vm.onUpdate("storage123");
            const emitted = wrapper.emitted();
            expect(emitted["updated"][0][0]).toEqual("storage123");
            expect(emitted["updated"][0][1]).toEqual(false);
        });

        it("should fire an update event when intermediate selection is updated", async () => {
            doMount(true);
            await wrapper.vm.onUpdateIntermediate("storage123");
            const emitted = wrapper.emitted();
            expect(emitted["updated"][0][0]).toEqual("storage123");
            expect(emitted["updated"][0][1]).toEqual(true);
        });
    });
});
