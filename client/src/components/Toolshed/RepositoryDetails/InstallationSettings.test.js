import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import InstallationSettings from "./InstallationSettings.vue";

vi.mock("@/composables/config", () => ({
    useConfig: () => ({
        config: {
            install_tool_dependencies: true,
            install_repository_dependencies: true,
            install_resolver_dependencies: true,
        },
        isConfigLoaded: true,
    }),
}));

const localVue = getLocalVue();

const { server, http } = useServerMock();

async function mountInstallationSettings() {
    const wrapper = mount(InstallationSettings, {
        global: localVue,
        props: {
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
    });
    await flushPromises();
    return wrapper;
}

/** Each dependency checkbox's label, mapped to whether it is checked. */
function dependencyOptions(wrapper) {
    return Object.fromEntries(
        wrapper
            .findAll(".custom-checkbox")
            .map((option) => [option.find("label").text(), option.find("input").element.checked]),
    );
}

describe("InstallationSettings", () => {
    beforeEach(() => {
        server.use(
            http.get("/api/configuration/dynamic_tool_confs", ({ response }) => {
                return response(200).json([]);
            }),
        );
    });

    it("titles the dialog with the repository and shows its long description, owner and revision", async () => {
        const wrapper = await mountInstallationSettings();

        expect(wrapper.find(".g-modal-title").text()).toBe("Installing 'name'");
        expect(wrapper.find(".description").text()).toBe("long_description");
        expect(wrapper.find(".revision").text()).toBe("owner rev. changesetRevision");
    });

    it("checks each dependency option the server configuration enables", async () => {
        const wrapper = await mountInstallationSettings();

        expect(dependencyOptions(wrapper)).toEqual({
            "Install resolvable dependencies": true,
            "Install repository dependencies": true,
            "Install tool dependencies": true,
        });
    });
});
