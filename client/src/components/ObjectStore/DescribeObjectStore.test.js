import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import { setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useQuotaUsageStore } from "@/stores/quotaUsageStore";

import DescribeObjectStore from "./DescribeObjectStore.vue";
import ObjectStoreBadges from "./ObjectStoreBadges.vue";

const localVue = getLocalVue();

const DESCRIPTION = "My cool **markdown**";

const TEST_STORAGE_API_RESPONSE_WITHOUT_ID = {
    object_store_id: null,
    private: false,
    description: DESCRIPTION,
    badges: [],
};

const TEST_STORAGE_API_RESPONSE_WITH_ID = {
    object_store_id: "foobar",
    private: false,
    description: DESCRIPTION,
    badges: [],
};
const TEST_STORAGE_API_RESPONSE_WITH_NAME = {
    object_store_id: "foobar",
    name: "my cool storage",
    description: DESCRIPTION,
    private: true,
    badges: [],
};
const TEST_STORAGE_API_RESPONSE_WITH_QUOTA = {
    object_store_id: "foobar",
    private: false,
    description: DESCRIPTION,
    badges: [],
    quota: { enabled: true, source: "lab" },
};

describe("DescribeObjectStore.vue", () => {
    let wrapper;
    let pinia;

    beforeEach(() => {
        pinia = createTestingPinia({ createSpy: vi.fn });
        setActivePinia(pinia);
    });

    async function mountWithResponse(response, extraProps = {}) {
        wrapper = shallowMount(DescribeObjectStore, {
            props: { storageInfo: response, what: "where i am throwing my test dataset", ...extraProps },
            global: withPlugins(localVue, pinia),
        });
    }

    it("test dataset storage with object store without id", async () => {
        await mountWithResponse(TEST_STORAGE_API_RESPONSE_WITHOUT_ID);
        expect(wrapper.findAll("loading-span-stub").length).toBe(0);
        const byIdSpan = wrapper.findAll(".display-os-by-id");
        expect(byIdSpan.length).toBe(0);
        const byNameSpan = wrapper.findAll(".display-os-by-name");
        expect(byNameSpan.length).toBe(0);
        const byDefaultSpan = wrapper.findAll(".display-os-default");
        expect(byDefaultSpan.length).toBe(1);
    });

    it("test dataset storage with object store id", async () => {
        await mountWithResponse(TEST_STORAGE_API_RESPONSE_WITH_ID);
        expect(wrapper.findAll("loading-span-stub").length).toBe(0);
        expect(wrapper.vm.storageInfo.object_store_id).toBe("foobar");
        const byIdSpan = wrapper.findAll(".display-os-by-id");
        expect(byIdSpan.length).toBe(1);
        const byNameSpan = wrapper.findAll(".display-os-by-name");
        expect(byNameSpan.length).toBe(0);
        expect(wrapper.vm.isPrivate).toBeFalsy();
    });

    it("test dataset storage with object store name", async () => {
        await mountWithResponse(TEST_STORAGE_API_RESPONSE_WITH_NAME);
        expect(wrapper.findAll("loading-span-stub").length).toBe(0);
        expect(wrapper.vm.storageInfo.object_store_id).toBe("foobar");
        const byIdSpan = wrapper.findAll(".display-os-by-id");
        expect(byIdSpan.length).toBe(0);
        const byNameSpan = wrapper.findAll(".display-os-by-name");
        expect(byNameSpan.length).toBe(1);
        expect(wrapper.vm.isPrivate).toBeTruthy();
        const configurationMarkupEl = wrapper.find("[markdown]");
        expect(configurationMarkupEl.attributes("markdown")).toBe(DESCRIPTION);
    });

    it("shows a spinner while the quota usage of its source is loading", async () => {
        useQuotaUsageStore().loadingBySource = { lab: true };
        await mountWithResponse(TEST_STORAGE_API_RESPONSE_WITH_QUOTA);
        expect(wrapper.findAll("loading-span-stub").length).toBe(1);
        expect(wrapper.text()).not.toContain("Galaxy has no quota configured");
    });

    it("hides the spinner once the quota usage of its source has loaded", async () => {
        useQuotaUsageStore().loadingBySource = { lab: false };
        await mountWithResponse(TEST_STORAGE_API_RESPONSE_WITH_QUOTA);
        expect(wrapper.findAll("loading-span-stub").length).toBe(0);
        expect(wrapper.text()).not.toContain("Galaxy has no quota configured");
    });

    it("lets badges open interactive popovers unless told otherwise", async () => {
        await mountWithResponse(TEST_STORAGE_API_RESPONSE_WITH_ID);
        expect(wrapper.findComponent(ObjectStoreBadges).props("interactive")).toBe(true);
        await mountWithResponse(TEST_STORAGE_API_RESPONSE_WITH_ID, { interactive: false });
        expect(wrapper.findComponent(ObjectStoreBadges).props("interactive")).toBe(false);
    });
});
