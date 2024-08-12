import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";

import { useServerMock } from "@/api/client/__mocks__";
import { setupSelectableMock } from "@/components/ObjectStore/mockServices";
import { ROOT_COMPONENT } from "@/utils/navigation";

import WorkflowSelectPreferredObjectStore from "./WorkflowSelectPreferredObjectStore.vue";

setupSelectableMock();

const localVue = getLocalVue(true);

const { server, http } = useServerMock();

function mountComponent() {
    server.use(
        http.get("/api/configuration", ({ response }) => {
            return response(200).json({});
        })
    );

    const wrapper = mount(WorkflowSelectPreferredObjectStore, {
        propsData: { invocationPreferredObjectStoreId: null },
        localVue,
    });
    return wrapper;
}

const PREFERENCES = ROOT_COMPONENT.preferences;

describe("WorkflowSelectPreferredObjectStore.vue", () => {
    it("updates object store to default on selection null", async () => {
        const wrapper = mountComponent();
        await flushPromises();
        const els = wrapper.findAll(PREFERENCES.object_store_selection.option_buttons.selector);
        expect(els.length).toBe(3);

        const galaxyDefaultOption = wrapper.find(
            PREFERENCES.object_store_selection.option_button({ object_store_id: "__null__" }).selector
        );
        expect(galaxyDefaultOption.exists()).toBeTruthy();
        await galaxyDefaultOption.trigger("click");
        await flushPromises();
        const errorEl = wrapper.find(".object-store-selection-error");
        expect(errorEl.exists()).toBeFalsy();
        const emitted = wrapper.emitted();
        expect(emitted["updated"][0][0]).toEqual(null);
    });
});
