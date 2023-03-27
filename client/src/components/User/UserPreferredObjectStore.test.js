import { setupSelectableMock } from "../ObjectStore/mockServices";
setupSelectableMock();

import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import flushPromises from "flush-promises";
import UserPreferredObjectStore from "./UserPreferredObjectStore.vue";

const localVue = getLocalVue(true);

const TEST_USER_ID = "myTestUserId";

function mountComponent() {
    const wrapper = mount(UserPreferredObjectStore, {
        propsData: { userId: TEST_USER_ID },
        localVue,
        stubs: { "b-popover": true },
    });
    return wrapper;
}

import { ROOT_COMPONENT } from "@/utils/navigation";

describe("UserPreferredObjectStore.vue", () => {
    let axiosMock;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
    });

    afterEach(async () => {
        axiosMock.restore();
    });

    it("contains a localized link", async () => {
        const wrapper = mountComponent();
        expect(wrapper.vm.$refs["modal"].isHidden).toBeTruthy();
        const el = await wrapper.find(ROOT_COMPONENT.preferences.object_store.selector);
        expect(el.text()).toBeLocalizationOf("Preferred Object Store");
        await el.trigger("click");
        expect(wrapper.vm.$refs["modal"].isHidden).toBeFalsy();
    });

    it("updates object store to default on selection null", async () => {
        const wrapper = mountComponent();
        const el = await wrapper.find(ROOT_COMPONENT.preferences.object_store.selector);
        await el.trigger("click");
        await flushPromises();
        const els = wrapper.findAll(ROOT_COMPONENT.preferences.object_store_selection.option_buttons.selector);
        expect(els.length).toBe(3);
        const galaxyDefaultOption = wrapper.find(
            ROOT_COMPONENT.preferences.object_store_selection.option_button({ object_store_id: "__null__" }).selector
        );
        expect(galaxyDefaultOption.exists()).toBeTruthy();
        axiosMock.onPut("/api/users/current", expect.objectContaining({ preferred_object_store_id: null })).reply(202);
        await galaxyDefaultOption.trigger("click");
        await flushPromises();
        const errorEl = wrapper.find(".object-store-selection-error");
        expect(errorEl.exists()).toBeFalsy();
    });

    it("updates object store to default on actual selection", async () => {
        const wrapper = mountComponent();
        const el = await wrapper.find(ROOT_COMPONENT.preferences.object_store.selector);
        await el.trigger("click");
        const objectStore2Option = wrapper.find(
            ROOT_COMPONENT.preferences.object_store_selection.option_button({ object_store_id: "object_store_2" })
                .selector
        );
        expect(objectStore2Option.exists()).toBeTruthy();
        axiosMock
            .onPut("/api/users/current", expect.objectContaining({ preferred_object_store_id: "object_store_2" }))
            .reply(202);
        await objectStore2Option.trigger("click");
        await flushPromises();
        const errorEl = wrapper.find(".object-store-selection-error");
        expect(errorEl.exists()).toBeFalsy();
    });

    it("displayed error is user update fails", async () => {
        const wrapper = mountComponent();
        const el = await wrapper.find(ROOT_COMPONENT.preferences.object_store.selector);
        await el.trigger("click");
        const galaxyDefaultOption = wrapper.find(
            ROOT_COMPONENT.preferences.object_store_selection.option_button({ object_store_id: "__null__" }).selector
        );
        expect(galaxyDefaultOption.exists()).toBeTruthy();
        axiosMock
            .onPut("/api/users/current", expect.objectContaining({ preferred_object_store_id: null }))
            .reply(400, { err_msg: "problem with selection.." });
        await galaxyDefaultOption.trigger("click");
        await flushPromises();
        const errorEl = await wrapper.find(".object-store-selection-error");
        expect(errorEl.exists()).toBeTruthy();
        expect(wrapper.vm.error).toBe("problem with selection..");
    });
});
