import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import ObjectStoreBadge from "./ObjectStoreBadge.vue";
import ObjectStoreBadges from "./ObjectStoreBadges.vue";

const globalConfig = getLocalVue();

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
            global: globalConfig.global,
        });
        const badgeListEl = wrapper.find(".object-store-badges");
        expect(badgeListEl.exists()).toBeTruthy();
        const badges = wrapper.findAllComponents(ObjectStoreBadge as any);
        expect(badges.length).toBe(2);
        expect(badges[0]!.attributes("size")).toBe("lg");
    });

    it("should pass along size attributes", async () => {
        wrapper = shallowMount(ObjectStoreBadges as object, {
            props: { badges: BADGES, size: "2x" },
            global: globalConfig.global,
        });
        const badgeListEl = wrapper.find(".object-store-badges");
        expect(badgeListEl.exists()).toBeTruthy();
        const badges = wrapper.findAllComponents(ObjectStoreBadge as any);
        expect(badges.length).toBe(2);
        expect(badges[0]!.attributes("size")).toBe("2x");
    });
});
