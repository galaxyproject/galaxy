import { mount } from "@vue/test-utils";
import InstallationSettings from "./InstallationSettings";
import { __RewireAPI__ as rewire } from "./InstallationSettings";

describe("InstallationSettings", () => {
    beforeEach(() => {
        rewire.__Rewire__("getGalaxyInstance", () => {
            return {
                config: {}
            };
        });
    });

    it("test tool repository installer interface", () => {
        const wrapper = mount(InstallationSettings, {
            propsData: {
                modalStatic: true,
                repo: {
                    long_description: "long_description",
                    description: "description",
                    owner: "owner",
                    name: "name"
                },
                changesetRevision: "changesetRevision",
                requiresPanel: true,
                toolshedUrl: "toolshedUrl"
            }
        });
        expect(wrapper.find(".title").text()).to.equal("Installing 'name'");
        expect(wrapper.find(".description").text()).to.equal("long_description");
        expect(wrapper.find(".revision").text()).to.equal("owner rev. changesetRevision");
    });
});
