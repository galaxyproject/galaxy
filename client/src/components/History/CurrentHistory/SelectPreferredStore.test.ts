import { mount } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";

import { useServerMock } from "@/api/client/__mocks__";
import { ROOT_COMPONENT } from "@/utils/navigation/schema";

import { setupSelectableMock } from "../../ObjectStore/mockServices";

import SelectPreferredStore from "./SelectPreferredStore.vue";

const { server, http } = useServerMock();

setupSelectableMock();

const localVue = getLocalVue(true);

const TEST_HISTORY_ID = "myTestHistoryId";

const TEST_HISTORY = {
    id: TEST_HISTORY_ID,
    preferred_object_store_id: null,
};

async function mountComponent() {
    server.use(
        http.get("/api/configuration", ({ response }) => {
            return response(200).json({});
        })
    );
    const wrapper = mount(SelectPreferredStore as object, {
        propsData: { userPreferredObjectStoreId: null, history: TEST_HISTORY },
        localVue,
    });

    await flushPromises();

    return wrapper;
}

const PREFERENCES = ROOT_COMPONENT.preferences;

describe("SelectPreferredStore.vue", () => {
    let axiosMock: MockAdapter;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
    });

    afterEach(async () => {
        axiosMock.restore();
    });

    it("updates object store to default on selection null", async () => {
        const wrapper = await mountComponent();
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
        expect(emitted["updated"]?.[0]?.[0]).toEqual(null);
    });

    it("updates object store to on non-null selection", async () => {
        const wrapper = await mountComponent();
        const els = wrapper.findAll(PREFERENCES.object_store_selection.option_buttons.selector);
        expect(els.length).toBe(3);
        const galaxyDefaultOption = wrapper.find(
            PREFERENCES.object_store_selection.option_button({ object_store_id: "object_store_2" }).selector
        );
        expect(galaxyDefaultOption.exists()).toBeTruthy();
        axiosMock
            .onPut(
                `/api/histories/${TEST_HISTORY_ID}`,
                expect.objectContaining({ preferred_object_store_id: "object_store_2" })
            )
            .reply(202);
        await galaxyDefaultOption.trigger("click");
        await flushPromises();
        const errorEl = wrapper.find(".object-store-selection-error");
        expect(errorEl.exists()).toBeFalsy();
        const emitted = wrapper.emitted();
        expect(emitted["updated"]?.[0]?.[0]).toEqual("object_store_2");
    });
});
