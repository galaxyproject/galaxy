import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import ObjectStoreRestrictionSpan from "./ObjectStoreRestrictionSpan";

const globalConfig = getLocalVue();

describe("ObjectStoreRestrictionSpan", () => {
    let wrapper;

    it("should render info about private storage if isPrivate", () => {
        wrapper = shallowMount(ObjectStoreRestrictionSpan, {
            props: { isPrivate: true },
            global: globalConfig.global,
        });
        expect(wrapper.find(".stored-how").text()).toMatch("private");
        expect(wrapper.find(".stored-how").attributes("title")).toBeTruthy();
    });

    it("should render info about unrestricted storage if not isPrivate", () => {
        wrapper = shallowMount(ObjectStoreRestrictionSpan, {
            props: { isPrivate: false },
            global: globalConfig.global,
        });
        expect(wrapper.find(".stored-how").text()).toMatch("sharable");
        expect(wrapper.find(".stored-how").attributes("title")).toBeTruthy();
    });
});
