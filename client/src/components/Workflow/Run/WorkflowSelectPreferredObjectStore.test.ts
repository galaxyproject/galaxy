import "@tests/vitest/mockHelpPopovers";

import { getLocalVue } from "@tests/vitest/helpers";
import { setupMockConfig } from "@tests/vitest/mockConfig";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, describe, expect, it } from "vitest";

import { setupSelectableMock } from "@/components/ObjectStore/mockServices";
import { ROOT_COMPONENT } from "@/utils/navigation/schema";

import WorkflowSelectPreferredObjectStore from "./WorkflowSelectPreferredObjectStore.vue";

setupSelectableMock();
setupMockConfig({});

enableAutoUnmount(afterEach);

const SELECTION = ROOT_COMPONENT.preferences.object_store_selection;
const SELECTION_ERROR = ".object-store-selection-error";

async function mountComponent(invocationPreferredObjectStoreId: string | null = null) {
    const wrapper = mount(WorkflowSelectPreferredObjectStore, {
        props: { invocationPreferredObjectStoreId },
        global: getLocalVue(true),
    });
    await flushPromises();
    return wrapper;
}

describe("WorkflowSelectPreferredObjectStore.vue", () => {
    it("lists the Galaxy default option and each selectable storage location", async () => {
        const wrapper = await mountComponent();

        expect(wrapper.findAll(SELECTION.option_cards.selector)).toHaveLength(3);
        expect(wrapper.find(SELECTION.option_card({ object_store_id: "__null__" }).selector).exists()).toBe(true);
    });

    it.each([
        { preferred: null, selected: "object_store_1", emitted: "object_store_1" },
        { preferred: "object_store_1", selected: "__null__", emitted: null },
    ])(
        "emits $emitted when $selected is selected while $preferred is preferred",
        async ({ preferred, selected, emitted }) => {
            const wrapper = await mountComponent(preferred);
            const selectButton = wrapper.find(SELECTION.option_card_select({ object_store_id: selected }).selector);
            expect(selectButton.exists()).toBe(true);

            await selectButton.trigger("click");
            await flushPromises();

            expect(wrapper.find(SELECTION_ERROR).exists()).toBe(false);
            expect(wrapper.emitted("updated")).toEqual([[emitted]]);
        },
    );
});
