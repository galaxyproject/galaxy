import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import { ROOT_COMPONENT } from "utils/navigation";

import ObjectStoreBadge from "./ObjectStoreBadge";

const localVue = getLocalVue(true);

const TEST_MESSAGE = "a test message provided by backend";

describe("ObjectStoreBadge", () => {
    let wrapper;

    function mountBadge(badge) {
        wrapper = mount(ObjectStoreBadge, {
            propsData: { badge },
            localVue,
            stubs: { "b-popover": true },
        });
    }

    it("should render a valid badge for more_secure type", async () => {
        mountBadge({ type: "more_secure", message: TEST_MESSAGE });
        const selector = ROOT_COMPONENT.object_store_details.badge_of_type({ type: "more_secure" }).selector;
        const iconEl = wrapper.find(selector);
        expect(iconEl.exists()).toBeTruthy();
        const popoverStub = wrapper.find("b-popover-stub");
        const popoverText = popoverStub.text();
        expect(popoverText).toContain(TEST_MESSAGE);
        expect(popoverText).toContain("more secure by the Galaxy administrator");
    });

    it("should render a valid badge for less_secure type", async () => {
        mountBadge({ type: "less_secure", message: TEST_MESSAGE });
        const selector = ROOT_COMPONENT.object_store_details.badge_of_type({ type: "less_secure" }).selector;
        const iconEl = wrapper.find(selector);
        expect(iconEl.exists()).toBeTruthy();
        const popoverStub = wrapper.find("b-popover-stub");
        const popoverText = popoverStub.text();
        expect(popoverText).toContain(TEST_MESSAGE);
        expect(popoverText).toContain("less secure by the Galaxy administrator");
    });

    it("should gracefully handle unspecified badge messages", async () => {
        mountBadge({ type: "more_secure", message: null });
        const selector = ROOT_COMPONENT.object_store_details.badge_of_type({ type: "more_secure" }).selector;
        const iconEl = wrapper.find(selector);
        expect(iconEl.exists()).toBeTruthy();
        const popoverStub = wrapper.find("b-popover-stub");
        expect(popoverStub.exists()).toBe(true);
    });
});
