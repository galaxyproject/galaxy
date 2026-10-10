import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import { BSpinner } from "bootstrap-vue";
import { describe, expect, it, vi } from "vitest";

import ConfigurationMarkdown from "./ConfigurationMarkdown.vue";
import DescribeObjectStore from "./DescribeObjectStore.vue";
import ObjectStoreRestrictionSpan from "./ObjectStoreRestrictionSpan.vue";

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

const SELECTORS = {
    BY_NAME: ".display-os-by-name",
    BY_ID: ".display-os-by-id",
    DEFAULT: ".display-os-default",
};

function countDescriptionSpans(wrapper) {
    return Object.fromEntries(
        Object.entries(SELECTORS).map(([key, selector]) => [key, wrapper.findAll(selector).length]),
    );
}

function mountWithResponse(storageInfo) {
    const pinia = createTestingPinia({ createSpy: vi.fn });
    return shallowMount(DescribeObjectStore, {
        props: { storageInfo, what: "where i am throwing my test dataset" },
        global: withPlugins(localVue, pinia),
    });
}

describe("DescribeObjectStore.vue", () => {
    it.each([
        [
            "the default storage when it has no id",
            TEST_STORAGE_API_RESPONSE_WITHOUT_ID,
            { BY_NAME: 0, BY_ID: 0, DEFAULT: 1 },
            false,
        ],
        [
            "the storage id when it has an id but no name",
            TEST_STORAGE_API_RESPONSE_WITH_ID,
            { BY_NAME: 0, BY_ID: 1, DEFAULT: 0 },
            false,
        ],
        [
            "the storage name when it has one",
            TEST_STORAGE_API_RESPONSE_WITH_NAME,
            { BY_NAME: 1, BY_ID: 0, DEFAULT: 0 },
            true,
        ],
    ])("describes %s", (_description, storageInfo, expectedSpans, isPrivate) => {
        const wrapper = mountWithResponse(storageInfo);

        expect(countDescriptionSpans(wrapper)).toEqual(expectedSpans);
        expect(wrapper.findComponent(ObjectStoreRestrictionSpan).props("isPrivate")).toBe(isPrivate);
    });

    it.each([
        ["no id", TEST_STORAGE_API_RESPONSE_WITHOUT_ID],
        ["an id", TEST_STORAGE_API_RESPONSE_WITH_ID],
        ["a name", TEST_STORAGE_API_RESPONSE_WITH_NAME],
    ])("says no quota is configured, without a usage spinner, for storage with %s", (_description, storageInfo) => {
        const wrapper = mountWithResponse(storageInfo);

        expect(wrapper.text()).toContain("Galaxy has no quota configured for this storage.");
        expect(wrapper.findComponent(BSpinner).exists()).toBe(false);
    });

    it("shows the storage id in bold", () => {
        const wrapper = mountWithResponse(TEST_STORAGE_API_RESPONSE_WITH_ID);

        expect(wrapper.find(`${SELECTORS.BY_ID} b`).text()).toBe("foobar");
    });

    it("shows the storage name instead of its id", () => {
        const wrapper = mountWithResponse(TEST_STORAGE_API_RESPONSE_WITH_NAME);

        expect(wrapper.find(`${SELECTORS.BY_NAME} b`).text()).toBe("my cool storage");
        expect(wrapper.text()).not.toContain("foobar");
    });

    it("renders the storage description as markdown", () => {
        const wrapper = mountWithResponse(TEST_STORAGE_API_RESPONSE_WITH_NAME);

        expect(wrapper.findComponent(ConfigurationMarkdown).props("markdown")).toBe(DESCRIPTION);
    });
});
