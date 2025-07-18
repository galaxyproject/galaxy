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

async function mountComponent(preferredObjectStoreId: string | null = null) {
    server.use(
        http.get("/api/configuration", ({ response }) => {
            return response(200).json({});
        })
    );

    server.use(
        http.get("/api/users/{user_id}/usage/{label}", ({ response }) => {
            return response(200).json({
                total_disk_usage: 0,
            });
        })
    );

    const wrapper = mount(SelectPreferredStore as object, {
        propsData: {
            preferredObjectStoreId: preferredObjectStoreId,
            history: TEST_HISTORY,
            showModal: true,
        },
        localVue,
        stubs: {
            BModal: {
                template: `
                    <div>
                        <slot></slot>
                        <div class="modal-footer">
                            <button class="btn btn-primary" @click="$emit('ok')">OK</button>
                        </div>
                    </div>
                `,
            },
        },
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
        const wrapper = await mountComponent("object_store_1");
        const els = wrapper.findAll(PREFERENCES.object_store_selection.option_cards.selector);
        expect(els.length).toBe(3);
        const galaxyDefaultOption = wrapper.find(
            PREFERENCES.object_store_selection.option_card_select({ object_store_id: "__null__" }).selector
        );
        expect(galaxyDefaultOption.exists()).toBeTruthy();
        axiosMock
            .onPut(`/api/histories/${TEST_HISTORY_ID}`, expect.objectContaining({ preferred_object_store_id: null }))
            .reply(202);
        await galaxyDefaultOption.trigger("click");
        await flushPromises();
        const errorEl = wrapper.find(".object-store-selection-error");
        expect(errorEl.exists()).toBeFalsy();

        const okButton = wrapper.find(".btn-primary");
        await okButton.trigger("click");

        await flushPromises();

        const emitted = wrapper.emitted();
        expect(emitted["updated"]?.[0]?.[0]).toEqual(null);
    });

    it("updates object store to on non-null selection", async () => {
        const wrapper = await mountComponent();
        const els = wrapper.findAll(PREFERENCES.object_store_selection.option_cards.selector);
        expect(els.length).toBe(3);
        const galaxyDefaultOption = wrapper.find(
            PREFERENCES.object_store_selection.option_card_select({ object_store_id: "object_store_2" }).selector
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

        const okButton = wrapper.find(".btn-primary");
        await okButton.trigger("click");

        await flushPromises();

        const emitted = wrapper.emitted();
        expect(emitted["updated"]?.[0]?.[0]).toEqual("object_store_2");
    });
});
