import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import { setupSelectableMock } from "../../ObjectStore/mockServices";
setupSelectableMock();

import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import flushPromises from "flush-promises";

import SelectPreferredStore from "./SelectPreferredStore.vue";

const localVue = getLocalVue(true);

const TEST_HISTORY_ID = "myTestHistoryId";

const TEST_HISTORY = {
    id: TEST_HISTORY_ID,
    preferred_object_store_id: null,
};

function mountComponent() {
    const wrapper = mount(SelectPreferredStore, {
        propsData: { userPreferredObjectStoreId: null, history: TEST_HISTORY },
        localVue,
    });
    return wrapper;
}

import { ROOT_COMPONENT } from "@/utils/navigation";

const PREFERENCES = ROOT_COMPONENT.preferences;

describe("SelectPreferredStore.vue", () => {
    let axiosMock;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
    });

    afterEach(async () => {
        axiosMock.restore();
    });

    it("updates object store to default on selection null", async () => {
        const wrapper = mountComponent();
        await flushPromises();
        const els = wrapper.findAll(PREFERENCES.object_store_selection.option_buttons.selector);
        expect(els.length).toBe(3);
        const galaxyDefaultOption = wrapper.find(
            PREFERENCES.object_store_selection.option_button({ object_store_id: "__null__" }).selector
        );
        expect(galaxyDefaultOption.exists()).toBeTruthy();
        axiosMock
            .onPut(`/api/histories/${TEST_HISTORY_ID}`, expect.objectContaining({ preferred_object_store_id: null }))
            .reply(202);
        await galaxyDefaultOption.trigger("click");
        await flushPromises();
        const errorEl = wrapper.find(".object-store-selection-error");
        expect(errorEl.exists()).toBeFalsy();
        const emitted = wrapper.emitted();
        expect(emitted["updated"][0][0]).toEqual(null);
    });
});
