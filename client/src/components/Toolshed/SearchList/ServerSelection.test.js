import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import ServerSelection from "./ServerSelection";

describe("ServerSelection", () => {
    it("test server selection dropdown", () => {
        const globalConfig = getLocalVue();
        const wrapper = mount(ServerSelection, {
            props: {
                toolshedUrl: "url_0",
                toolshedUrls: ["url_0", "url_1"],
                loading: false,
                total: 10,
            },
            global: globalConfig.global,
        });
        expect(wrapper.find(".description").text()).toBe("10 repositories available at");
        const $options = wrapper.findAll("a");
        expect($options[0].text()).toBe("url_0");
        expect($options[1].text()).toBe("url_0");
        expect($options[2].text()).toBe("url_1");
        expect(wrapper.vm.showDropdown).toBe(true);
        const $link = wrapper.find(".dropdown-item:last-child");
        $link.trigger("click");
        expect(wrapper.emitted().onToolshed[0]).toEqual(expect.arrayContaining(["url_1"]));
    });
});
