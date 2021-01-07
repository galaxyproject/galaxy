import { mount } from "@vue/test-utils";
import InstallationSettings from "./InstallationSettings";

jest.mock("app");

describe("InstallationSettings", () => {
    it("test tool repository installer interface", () => {
        const wrapper = mount(InstallationSettings, {
            propsData: {
                modalStatic: true,
                repo: {
                    long_description: "long_description",
                    description: "description",
                    owner: "owner",
                    name: "name",
                },
                changesetRevision: "changesetRevision",
                requiresPanel: true,
                toolshedUrl: "toolshedUrl",
            },
        });
        expect(wrapper.find(".title").text()).toBe("Installing 'name'");
        expect(wrapper.find(".description").text()).toBe("long_description");
        expect(wrapper.find(".revision").text()).toBe("owner rev. changesetRevision");
    });
});
