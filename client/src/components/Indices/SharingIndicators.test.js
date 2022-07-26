import SharingIndicators from "./SharingIndicators";
import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";

const localVue = getLocalVue();

describe("SharingIndicators.vue", () => {
    let wrapper;

    describe("buttons not visible when object unshared", () => {
        beforeEach(async () => {
            const propsData = {
                object: {
                    published: false,
                    shared: false,
                },
            };
            wrapper = shallowMount(SharingIndicators, {
                propsData,
                localVue,
            });
        });

        it("should not have display published button", async () => {
            expect(wrapper.find(".sharing-indicator-published").exists()).toBeFalsy();
        });

        it("should not have display shared button", async () => {
            expect(wrapper.find(".sharing-indicator-shared").exists()).toBeFalsy();
        });
    });

    describe("shared objects", () => {
        beforeEach(async () => {
            const propsData = {
                object: {
                    published: true,
                    shared: true,
                },
            };
            wrapper = shallowMount(SharingIndicators, {
                propsData,
                localVue,
            });
        });

        it("should fire a is:published filter on published click", async () => {
            await wrapper.find(".sharing-indicator-published").trigger("click");
            const emitted = wrapper.emitted("filter");
            expect(emitted[0][0]).toBe("is:published");
        });

        it("should fire a is:shared_with_me filter on shared click", async () => {
            await wrapper.find(".sharing-indicator-shared").trigger("click");
            const emitted = wrapper.emitted("filter");
            expect(emitted[0][0]).toBe("is:shared_with_me");
        });
    });
});
