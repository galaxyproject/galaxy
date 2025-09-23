import "tests/jest/mockHelpPopovers";

import { getLocalVue } from "@tests/jest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setupMockConfig } from "tests/jest/mockConfig";

import { setupSelectableMock } from "@/components/ObjectStore/mockServices";
import { ROOT_COMPONENT } from "@/utils/navigation/schema";

import WorkflowSelectPreferredObjectStore from "./WorkflowSelectPreferredObjectStore.vue";

setupSelectableMock();
setupMockConfig({});

const localVue = getLocalVue(true);

function mountComponent() {
    const wrapper = mount(WorkflowSelectPreferredObjectStore as object, {
        propsData: { invocationPreferredObjectStoreId: null },
        localVue,
    });
    return wrapper;
}

const PREFERENCES = ROOT_COMPONENT.preferences;

describe("WorkflowSelectPreferredObjectStore.vue", () => {
    it("update preferred object store on selection", async () => {
        const wrapper = mountComponent();

        await flushPromises();
        const els = wrapper.findAll(PREFERENCES.object_store_selection.option_cards.selector);
        expect(els.length).toBe(3);

        const galaxyDefaultOption = wrapper.find(
            PREFERENCES.object_store_selection.option_card({ object_store_id: "__null__" }).selector
        );

        expect(galaxyDefaultOption.exists()).toBeTruthy();

        const objectStoreOptionButton = wrapper.find(
            ROOT_COMPONENT.preferences.object_store_selection.option_card_select({ object_store_id: "object_store_1" })
                .selector
        );

        expect(objectStoreOptionButton.exists()).toBeTruthy();

        await objectStoreOptionButton.trigger("click");
        await flushPromises();

        const errorEl = wrapper.find(".object-store-selection-error");
        expect(errorEl.exists()).toBeFalsy();

        const emitted = wrapper.emitted();
        expect(emitted["updated"]?.[0]?.[1]).toBeFalsy();
    });
});
