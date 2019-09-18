import { mount } from "@vue/test-utils";
import InstallationButton from "./InstallationButton";
import Vue from "vue";

describe("InstallationButton", () => {
    let wrapper;
    let emitted;

    it("test installed repository revision", () => {
        wrapper = mount(InstallationButton, {
            propsData: {
                installed: true,
                status: "Installed"
            }
        });
        emitted = wrapper.emitted();
        const $el = wrapper.find("button");
        expect($el.classes()).to.include("btn-danger");
        $el.trigger("click");
        expect(wrapper.emitted().onUninstall).to.not.be.undefined;
    });

    it("test uninstalled repository revision", () => {
        wrapper = mount(InstallationButton, {
            propsData: {
                installed: false,
                status: "Uninstalled"
            }
        });
        emitted = wrapper.emitted();
        const $el = wrapper.find("button");
        expect($el.classes()).to.include("btn-primary");
        $el.trigger("click");
        expect(wrapper.emitted().onInstall).to.not.be.undefined;
    });
});
