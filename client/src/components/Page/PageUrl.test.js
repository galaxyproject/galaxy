import PageUrl from "./PageUrl";
import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

const localVue = getLocalVue(true);

describe("PageUrl.vue", () => {
    let wrapper;

    beforeEach(async () => {
        const propsData = {
            root: "/rootprefix/",
            owner: "jmchilton",
            slug: "my-cool-slug",
        };
        wrapper = mount(PageUrl, {
            propsData,
            localVue,
        });
    });

    describe("component", () => {
        it("should localize title text", async () => {
            expect(wrapper.getComponent(".page-url-copy").attributes("title")).toBeLocalized();
        });

        it("should emit an event when owner is clicked on", async () => {
            const ownerEl = wrapper.getComponent("a.page-url-owner");
            expect(ownerEl.text()).toBe("jmchilton");
            await ownerEl.trigger("click");

            const emitted = wrapper.emitted();
            expect(emitted["click-owner"][0][0]).toEqual("jmchilton");
        });
    });
});
