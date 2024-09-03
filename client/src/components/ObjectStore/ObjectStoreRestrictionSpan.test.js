import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import ObjectStoreRestrictionSpan from "./ObjectStoreRestrictionSpan";

const localVue = getLocalVue();

describe("ObjectStoreRestrictionSpan", () => {
    let wrapper;

    it("should render info about private storage if isPrivate", () => {
        wrapper = shallowMount(ObjectStoreRestrictionSpan, {
            propsData: { isPrivate: true },
            localVue,
        });
        expect(wrapper.find(".stored-how").text()).toMatch("private");
        expect(wrapper.find(".stored-how").attributes("title")).toBeTruthy();
    });

    it("should render info about unrestricted storage if not isPrivate", () => {
        wrapper = shallowMount(ObjectStoreRestrictionSpan, {
            propsData: { isPrivate: false },
            localVue,
        });
        expect(wrapper.find(".stored-how").text()).toMatch("sharable");
        expect(wrapper.find(".stored-how").attributes("title")).toBeTruthy();
    });
});
