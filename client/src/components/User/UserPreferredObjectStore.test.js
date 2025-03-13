import "tests/jest/mockHelpPopovers";

import { getFakeRegisteredUser } from "@tests/test-data";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";

import { useServerMock } from "@/api/client/__mocks__";
import { ROOT_COMPONENT } from "@/utils/navigation";

import { setupSelectableMock } from "../ObjectStore/mockServices";

import UserPreferredObjectStore from "./UserPreferredObjectStore.vue";

setupSelectableMock();

const localVue = getLocalVue(true);

const { server, http } = useServerMock();

const TEST_USER_ID = "myTestUserId";

function mountComponent() {
    server.use(
        http.get("/api/configuration", ({ response }) => {
            return response(200).json({});
        })
    );

    const wrapper = mount(UserPreferredObjectStore, {
        propsData: { userId: TEST_USER_ID },
        localVue,
        stubs: { "b-popover": true },
    });
    return wrapper;
}

describe("UserPreferredObjectStore.vue", () => {
    it("contains a localized link", async () => {
        const wrapper = mountComponent();
        expect(wrapper.vm.$refs["modal"].isHidden).toBeTruthy();
        const el = await wrapper.find(ROOT_COMPONENT.preferences.object_store.selector);
        expect(el.text()).toBeLocalizationOf("Preferred Galaxy Storage");
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
        const el = await wrapper.find(ROOT_COMPONENT.preferences.object_store.selector);
        await el.trigger("click");
        const objectStore2Option = wrapper.find(
            ROOT_COMPONENT.preferences.object_store_selection.option_button({ object_store_id: "object_store_2" })
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

    it("displayed error is user update fails", async () => {
        const wrapper = mountComponent();
        const el = await wrapper.find(ROOT_COMPONENT.preferences.object_store.selector);
        await el.trigger("click");
        const galaxyDefaultOption = wrapper.find(
            ROOT_COMPONENT.preferences.object_store_selection.option_button({ object_store_id: "__null__" }).selector
        );
        expect(galaxyDefaultOption.exists()).toBeTruthy();

        server.use(
            http.put("/api/users/{user_id}", ({ response }) => {
                return response("4XX").json({ err_msg: "problem with selection.." }, { status: 400 });
            })
        );

        await galaxyDefaultOption.trigger("click");
        await flushPromises();
        const errorEl = await wrapper.find(".object-store-selection-error");
        expect(errorEl.exists()).toBeTruthy();
        expect(wrapper.vm.error).toBe("problem with selection..");
    });
});
