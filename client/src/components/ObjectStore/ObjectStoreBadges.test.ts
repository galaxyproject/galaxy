import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, shallowMount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import type { ObjectStoreBadgeType } from "@/api/objectStores.templates";

import ObjectStoreBadge from "./ObjectStoreBadge.vue";
import ObjectStoreBadges from "./ObjectStoreBadges.vue";

enableAutoUnmount(afterEach);

const BADGE_LIST = ".object-store-badges";

const TEST_MESSAGE = "a test message provided by backend";
const BADGES: ObjectStoreBadgeType[] = [
    { type: "more_secure", message: TEST_MESSAGE, source: "admin" },
    { type: "slower", message: TEST_MESSAGE, source: "admin" },
];

function mountBadges(props: { size?: string } = {}) {
    return shallowMount(ObjectStoreBadges, {
        props: { badges: BADGES, ...props },
        global: getLocalVue(),
    });
}

function renderedBadges(wrapper: ReturnType<typeof mountBadges>) {
    return wrapper
        .findAllComponents(ObjectStoreBadge)
        .map((badge) => ({ badge: badge.props("badge"), size: badge.attributes("size") }));
}

describe("ObjectStoreBadges", () => {
    it("renders every badge at the default lg size when no size is given", () => {
        const wrapper = mountBadges();

        expect(wrapper.find(BADGE_LIST).exists()).toBe(true);
        expect(renderedBadges(wrapper)).toEqual([
            { badge: BADGES[0], size: "lg" },
            { badge: BADGES[1], size: "lg" },
        ]);
    });

    it("passes an explicit size to every badge", () => {
        const wrapper = mountBadges({ size: "2x" });

        expect(wrapper.find(BADGE_LIST).exists()).toBe(true);
        expect(renderedBadges(wrapper)).toEqual([
            { badge: BADGES[0], size: "2x" },
            { badge: BADGES[1], size: "2x" },
        ]);
    });
});
