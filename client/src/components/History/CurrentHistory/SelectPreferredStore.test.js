import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import SelectPreferredStore from "./SelectPreferredStore";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import flushPromises from "flush-promises";

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

import { ROOT_COMPONENT } from "utils/navigation";

const OBJECT_STORES = [
    { object_store_id: "object_store_1", badges: [], quota: { enabled: false } },
    { object_store_id: "object_store_2", badges: [], quota: { enabled: false } },
];

describe("SelectPreferredStore.vue", () => {
    let axiosMock;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
        axiosMock.onGet("/api/object_store?selectable=true").reply(200, OBJECT_STORES);
    });

    afterEach(async () => {
        axiosMock.restore();
    });

    it("updates object store to default on selection null", async () => {
        const wrapper = mountComponent();
        await flushPromises();
        const els = wrapper.findAll(ROOT_COMPONENT.preferences.object_store_selection.option_buttons.selector);
        expect(els.length).toBe(3);
        const galaxyDefaultOption = wrapper.find(
            ROOT_COMPONENT.preferences.object_store_selection.option_button({ object_store_id: "__null__" }).selector
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
