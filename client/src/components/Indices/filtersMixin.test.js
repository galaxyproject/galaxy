import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import filtersMixin from "./filtersMixin";

const localVue = getLocalVue();

const Component = {
    render() {},
    mixins: [filtersMixin],
};

describe("filtersMixin.js", () => {
    let wrapper;

    beforeEach(async () => {
        const propsData = {};
        wrapper = shallowMount(Component, propsData, localVue);
    });

    it("should be initially unfiltered", async () => {
        expect(wrapper.vm.isFiltered).toBeFalsy();
    });

    it("should combine implicit and explicit filter", async () => {
        expect(wrapper.vm.filter).toBe("");
        wrapper.vm.appendTagFilter("name", "foobar");
        expect(wrapper.vm.filter).toBe("name:'foobar'");
    });

    it("should be filtered after setting a filter", async () => {
        wrapper.vm.appendTagFilter("name", "foobar");
        expect(wrapper.vm.isFiltered).toBeTruthy();
    });

    it("should be filter space", async () => {
        wrapper.vm.appendFilter("bar");
        wrapper.vm.appendFilter("foo");
        expect(wrapper.vm.filter).toBe("foo bar");
    });

    it("should not duplicate tagged filters if added twice", async () => {
        wrapper.vm.appendTagFilter("name", "foobar");
        wrapper.vm.appendTagFilter("name", "foobar");
        expect(wrapper.vm.filter).toBe("name:'foobar'");
    });
});
