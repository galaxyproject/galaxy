import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { disposePinia } from "pinia";
import { afterEach, describe, expect, it, onTestFinished, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import ShowSelectedObjectStore from "./ShowSelectedObjectStore.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import DescribeObjectStore from "@/components/ObjectStore/DescribeObjectStore.vue";

const { server, http } = useServerMock();

const localVue = getLocalVue(true);
const TEST_OBJECT_ID = "os123";
const TEST_USER_OBJECT_STORE_ID = "user_objects://34";

const OBJECT_STORE_DATA = {
    description: null,
    object_store_id: TEST_OBJECT_ID,
    badges: [],
    private: false,
    quota: {
        enabled: false,
    },
};

const USER_OBJECT_STORE_DATA = {
    description: null,
    object_store_id: TEST_USER_OBJECT_STORE_ID,
    badges: [],
    private: false,
    quota: {
        enabled: false,
    },
    active: true,
    hidden: false,
    purged: false,
    secrets: [],
    template_id: "disk",
    template_version: 1,
    type: "disk",
    uuid: "34",
    variables: {},
};

function mountWithPreferredStoreId(preferredObjectStoreId) {
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    onTestFinished(() => disposePinia(pinia));
    return mount(ShowSelectedObjectStore, {
        props: { preferredObjectStoreId, forWhat: "Data goes into..." },
        global: withPlugins(localVue, pinia),
    });
}

describe("ShowSelectedObjectStore", () => {
    enableAutoUnmount(afterEach);

    it("shows loading before describing the selected Galaxy object store", async () => {
        server.use(
            http.get("/api/object_stores/{object_store_id}", ({ response }) => {
                return response(200).json(OBJECT_STORE_DATA);
            }),
        );
        const wrapper = mountWithPreferredStoreId(TEST_OBJECT_ID);
        const loadingEl = wrapper.findComponent(LoadingSpan);
        expect(loadingEl.exists()).toBeTruthy();
        expect(loadingEl.get(".loading-message").text()).toContain("Loading Galaxy storage details");
        await flushPromises();
        expect(wrapper.findComponent(LoadingSpan).exists()).toBeFalsy();
        expect(wrapper.findComponent(DescribeObjectStore).exists()).toBeTruthy();
        // Shown inside hover popovers, which can't hold another interactive popover.
        expect(wrapper.findComponent(DescribeObjectStore).props("interactive")).toBe(false);
    });

    it("loads URI IDs through the user object-store instance API", async () => {
        server.use(
            http.get("/api/object_store_instances/{user_object_store_id}", ({ response }) => {
                return response(200).json(USER_OBJECT_STORE_DATA);
            }),
        );

        const wrapper = mountWithPreferredStoreId(TEST_USER_OBJECT_STORE_ID);
        const loadingEl = wrapper.findComponent(LoadingSpan);
        expect(loadingEl.exists()).toBeTruthy();
        expect(loadingEl.get(".loading-message").text()).toContain("Loading Galaxy storage details");
        await flushPromises();
        expect(wrapper.findComponent(LoadingSpan).exists()).toBeFalsy();
        expect(wrapper.findComponent(DescribeObjectStore).exists()).toBeTruthy();
    });
});
