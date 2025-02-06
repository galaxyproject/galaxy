import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import InstallationSettings from "./InstallationSettings";

jest.mock("app");
// Mock the useConfig composable
jest.mock("@/composables/config", () => ({
    useConfig: () => ({
        config: {
            install_tool_dependencies: true,
            install_repository_dependencies: true,
            install_resolver_dependencies: true
        },
        isConfigLoaded: true
    })
}));

const localVue = getLocalVue();

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
                currentPanel: {},
            },
            localVue,
        });
        expect(wrapper.find(".title").text()).toBe("Installing 'name'");
        expect(wrapper.find(".description").text()).toBe("long_description");
        expect(wrapper.find(".revision").text()).toBe("owner rev. changesetRevision");

        expect(wrapper.vm.installToolDependencies).toBe(true);
        expect(wrapper.vm.installRepositoryDependencies).toBe(true);
        expect(wrapper.vm.installResolverDependencies).toBe(true);
    });
});
