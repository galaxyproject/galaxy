import "tests/jest/mockHelpPopovers";

import { getLocalVue } from "@tests/jest/helpers";
import { getFakeRegisteredUser } from "@tests/test-data";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";

import { useServerMock } from "@/api/client/__mocks__";
import { setupSelectableMock } from "@/components/ObjectStore/mockServices";
import { ROOT_COMPONENT } from "@/utils/navigation/schema";

import UserPreferredObjectStore from "./UserPreferredObjectStore.vue";

setupSelectableMock();

const localVue = getLocalVue(true);

const { server, http } = useServerMock();

function mountComponent() {
    server.use(
        http.get("/api/configuration", ({ response }) => {
            return response(200).json({});
        })
    );

    const wrapper = mount(UserPreferredObjectStore as object, {
        localVue,
    });
    return wrapper;
}

describe("UserPreferredObjectStore.vue", () => {
    it("contains a localized link", async () => {
        const wrapper = mountComponent();

        expect(
            wrapper.find(ROOT_COMPONENT.preferences.object_store_selection.modal.selector).attributes("aria-hidden")
        ).toBeTruthy();

        const el = wrapper.find(ROOT_COMPONENT.preferences.object_store.selector);
        (expect(el.text()) as any).toBeLocalizationOf("Preferred Galaxy Storage");

        await el.trigger("click");

        expect(
            wrapper.find(ROOT_COMPONENT.preferences.object_store_selection.modal.selector).attributes("aria-hidden")
        ).toBeFalsy();
    });

    it("updates object store to default on selection null", async () => {
        const wrapper = mountComponent();
        const el = wrapper.find(ROOT_COMPONENT.preferences.object_store.selector);

        await el.trigger("click");
        await flushPromises();

        const els = wrapper.findAll(ROOT_COMPONENT.preferences.object_store_selection.option_cards.selector);
        expect(els.length).toBe(3);

        const galaxyDefaultOption = wrapper.find(
            ROOT_COMPONENT.preferences.object_store_selection.option_card({ object_store_id: "__null__" }).selector
        );

        expect(galaxyDefaultOption.exists()).toBeTruthy();

        server.use(
            http.put("/api/users/{user_id}", ({ response }) => {
                return response(200).json(getFakeRegisteredUser({ preferred_object_store_id: null }));
            })
        );

        await galaxyDefaultOption.trigger("click");
        await flushPromises();

        const errorEl = wrapper.find(".object-store-selection-error");
        expect(errorEl.exists()).toBeFalsy();
    });

    it("updates object store to default on actual selection", async () => {
        const wrapper = mountComponent();
        const el = wrapper.find(ROOT_COMPONENT.preferences.object_store.selector);

        await el.trigger("click");

        const objectStore2Option = wrapper.find(
            ROOT_COMPONENT.preferences.object_store_selection.option_card({ object_store_id: "object_store_2" })
                .selector
        );

        expect(objectStore2Option.exists()).toBeTruthy();

        server.use(
            http.put("/api/users/{user_id}", ({ response }) => {
                return response(200).json(getFakeRegisteredUser({ preferred_object_store_id: "object_store_2" }));
            })
        );

        await objectStore2Option.trigger("click");
        await flushPromises();

        const errorEl = wrapper.find(".object-store-selection-error");
        expect(errorEl.exists()).toBeFalsy();
    });

    it("displayed error if user update fails", async () => {
        const wrapper = mountComponent();
        const el = wrapper.find(ROOT_COMPONENT.preferences.object_store.selector);

        await el.trigger("click");

        const galaxyDefaultOption = wrapper.find(
            ROOT_COMPONENT.preferences.object_store_selection.option_card({ object_store_id: "__null__" }).selector
        );
        const objectStoreOptionOption = wrapper.find(
            ROOT_COMPONENT.preferences.object_store_selection.option_card({ object_store_id: "object_store_1" })
                .selector
        );

        expect(galaxyDefaultOption.exists()).toBeTruthy();

        expect(objectStoreOptionOption.exists()).toBeTruthy();

        server.use(
            http.put("/api/users/{user_id}", ({ response }) => {
                return response("4XX").json({ err_msg: "problem with selection..", err_code: 400 }, { status: 400 });
            })
        );

        const objectStoreOptionButton = wrapper.find(
            ROOT_COMPONENT.preferences.object_store_selection.option_card_select({ object_store_id: "object_store_1" })
                .selector
        );

        await objectStoreOptionButton.trigger("click");

        await galaxyDefaultOption.trigger("click");
        await flushPromises();

        const errorEl = wrapper.find(".object-store-selection-error");
        expect(errorEl.exists()).toBeTruthy();
        expect(errorEl.text()).toContain("problem with selection..");
    });
});
