import { mount, type Wrapper } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import type Vue from "vue";

import type { ObjectStoreBadgeType } from "@/api/objectStores.templates";
import { MESSAGES } from "@/components/ObjectStore/badgeMessages";

import ObjectStoreBadge from "./ObjectStoreBadge.vue";

const localVue = getLocalVue(true);

const TEST_MESSAGE = "This is a test message for the badge.";

async function mountBadge(badge: ObjectStoreBadgeType) {
    const wrapper = mount(ObjectStoreBadge as object, {
        propsData: { badge },
        localVue,
    });

    return wrapper;
}

async function getTooltip(wrapper: Wrapper<Vue>) {
    const badge = wrapper.find(".object-store-badge-wrapper");

    return badge.attributes("data-mock-directive");
}

describe("ObjectStoreBadge", () => {
    it("should render a valid badge for more_secure type", async () => {
        const wrapper = await mountBadge({ type: "more_secure", message: TEST_MESSAGE, source: "admin" });

        const tooltip = await getTooltip(wrapper);

        expect(tooltip).toContain(TEST_MESSAGE);
        expect(tooltip).toContain(MESSAGES.more_secure);
    });

    it("should render a valid badge for less_secure type", async () => {
        const wrapper = await mountBadge({ type: "less_secure", message: TEST_MESSAGE, source: "admin" });

        const tooltip = await getTooltip(wrapper);

        expect(tooltip).toContain(TEST_MESSAGE);
        expect(tooltip).toContain(MESSAGES.less_secure);
    });

    it("should gracefully handle unspecified/null badge messages", async () => {
        const wrapper = await mountBadge({ type: "more_secure", message: null, source: "admin" });

        const tooltip = await getTooltip(wrapper);

        expect(tooltip).toContain("This storage has been marked as more secure by the Galaxy administrator.");
        expect(tooltip).toContain(MESSAGES.more_secure);
    });
});
