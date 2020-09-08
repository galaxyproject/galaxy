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
        expect($el.classes()).toEqual(expect.arrayContaining(["btn-danger"]));
        $el.trigger("click");
        expect(wrapper.emitted().onUninstall).toBeDefined();
    });

    it("test uninstalled repository revision", () => {
        const wrapper = mount(InstallationButton, {
            propsData: {
                installed: false,
                status: "Uninstalled",
            },
        });
        const $el = wrapper.find("button");
        expect($el.classes()).toEqual(expect.arrayContaining(["btn-primary"]));
        $el.trigger("click");
        expect(wrapper.emitted().onInstall).toBeDefined();
    });
});
