import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import ServerSelection from "./ServerSelection";

const localVue = getLocalVue();

describe("ServerSelection", () => {
    it("test server selection dropdown", () => {
        const wrapper = mount(ServerSelection, {
            propsData: {
                toolshedUrl: "url_0",
                toolshedUrls: ["url_0", "url_1"],
                loading: false,
                total: 10,
            },
            localVue,
        });
        expect(wrapper.find(".description").text()).toBe("10 repositories available at");
        const $options = wrapper.findAll("a");
        expect($options.at(0).text()).toBe("url_0");
        expect($options.at(1).text()).toBe("url_0");
        expect($options.at(2).text()).toBe("url_1");
        expect(wrapper.vm.showDropdown).toBe(true);
        const $link = wrapper.find(".dropdown-item:last-child");
        $link.trigger("click");
        expect(wrapper.emitted().onToolshed[0]).toEqual(expect.arrayContaining(["url_1"]));
    });
});
