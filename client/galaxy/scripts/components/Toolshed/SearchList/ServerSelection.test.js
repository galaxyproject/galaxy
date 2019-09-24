import { mount } from "@vue/test-utils";
import ServerSelection from "./ServerSelection";

describe("ServerSelection", () => {
    it("test server selection dropdown", () => {
        const wrapper = mount(ServerSelection, {
            propsData: {
                toolshedUrl: "url_0",
                toolshedUrls: ["url_0", "url_1"],
                loading: false,
                total: "total"
            }
        });
        expect(wrapper.find(".description").text()).to.equal("total repositories available at");
        const $options = wrapper.findAll("a");
        expect($options.at(0).text()).to.equal("url_0");
        expect($options.at(1).text()).to.equal("url_0");
        expect($options.at(2).text()).to.equal("url_1");
        expect(wrapper.vm.showDropdown).to.be.true;
        const $link = wrapper.find(".dropdown-item:last-child");
        $link.trigger("click");
        expect(wrapper.emitted().onToolshed[0]).to.contain("url_1");
    });
});
