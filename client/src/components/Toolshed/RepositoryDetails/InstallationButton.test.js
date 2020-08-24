import { mount } from "@vue/test-utils";
import InstallationButton from "./InstallationButton";

describe("InstallationButton", () => {
    it("test installed repository revision", () => {
        const wrapper = mount(InstallationButton, {
            propsData: {
                installed: true,
                status: "Installed",
            },
        });
        const $el = wrapper.find("button");
        expect($el.classes()).to.include("btn-danger");
        $el.trigger("click");
        expect(wrapper.emitted().onUninstall).to.not.be.undefined;
    });

    it("test uninstalled repository revision", () => {
        const wrapper = mount(InstallationButton, {
            propsData: {
                installed: false,
                status: "Uninstalled",
            },
        });
        const $el = wrapper.find("button");
        expect($el.classes()).to.include("btn-primary");
        $el.trigger("click");
        expect(wrapper.emitted().onInstall).to.not.be.undefined;
    });
});
