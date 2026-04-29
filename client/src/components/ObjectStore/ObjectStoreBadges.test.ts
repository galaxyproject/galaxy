import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import ObjectStoreBadge from "./ObjectStoreBadge.vue";
import ObjectStoreBadges from "./ObjectStoreBadges.vue";

const localVue = getLocalVue(true);

const TEST_MESSAGE = "a test message provided by backend";
const BADGES = [
    { type: "more_secure", message: TEST_MESSAGE },
    { type: "slower", message: TEST_MESSAGE },
];

describe("ObjectStoreBadges", () => {
    let wrapper;

    it("should render all badges in array", async () => {
        wrapper = shallowMount(ObjectStoreBadges as object, {
            props: { badges: BADGES },
            global: localVue,
        });
        const badgeListEl = wrapper.find(".object-store-badges");
        expect(badgeListEl.exists()).toBeTruthy();
        const badges = wrapper.findAllComponents(ObjectStoreBadge);
        expect(badges.length).toBe(2);
        expect(badges.at(0).attributes("size")).toBe("lg");
    });

    it("should pass along size attributes", async () => {
        wrapper = shallowMount(ObjectStoreBadges as object, {
            props: { badges: BADGES, size: "2x" },
            global: localVue,
        });
        const badgeListEl = wrapper.find(".object-store-badges");
        expect(badgeListEl.exists()).toBeTruthy();
        const badges = wrapper.findAllComponents(ObjectStoreBadge);
        expect(badges.length).toBe(2);
        expect(badges.at(0).attributes("size")).toBe("2x");
    });
});
