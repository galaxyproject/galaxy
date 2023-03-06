import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import ObjectStoreBadges from "./ObjectStoreBadges";

const localVue = getLocalVue(true);

const TEST_MESSAGE = "a test message provided by backend";
const BADGES = [
    { type: "more_secure", message: TEST_MESSAGE },
    { type: "slower", message: TEST_MESSAGE },
];

describe("ObjectStoreBadges", () => {
    let wrapper;

    function mountBadges() {
        wrapper = mount(ObjectStoreBadges, {
            propsData: { badges: BADGES },
            localVue,
            stubs: { ObjectStoreBadge: true },
        });
    }

    it("should render all badges in array", async () => {
        mountBadges();
        const badgeListEl = wrapper.find(".object-store-badges");
        expect(badgeListEl.exists()).toBeTruthy();
        console.log(badgeListEl.html());
        expect(badgeListEl.findAll("objectstorebadge-stub").length).toBe(2);
    });
});
