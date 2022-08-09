import { mount, createLocalVue } from "@vue/test-utils";
import InstallationButton from "./InstallationButton";
import { localizationPlugin } from "components/plugins";

const localVue = createLocalVue();
localVue.use(localizationPlugin);

describe("InstallationButton", () => {


    it("test installed repository revision", () => {
        const wrapper = mount(InstallationButton, {
            propsData: {
                installed: true,
                status: "Installed",
            },
            localVue,
        });
        const $el = wrapper.find("button:nth-of-type(2)");
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
            localVue,
        });
        const $el = wrapper.find("button:nth-of-type(1)");
        expect($el.classes()).toEqual(expect.arrayContaining(["btn-primary"]));
        $el.trigger("click");
        expect(wrapper.emitted().onInstall).toBeDefined();
    });
});
