import "@/composables/__mocks__/filter";

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

        const sectionInput = wrapper.get("#install-tool-section");
        expect(wrapper.get('label[for="install-tool-section"]').text()).toBe("Target Section:");
        expect(sectionInput.element.closest('[role="combobox"]')).not.toBeNull();
    });

    it("checks each dependency option the server configuration enables", async () => {
        const wrapper = await mountInstallationSettings();

        expect(dependencyOptions(wrapper)).toEqual({
            "Install resolvable dependencies": true,
            "Install repository dependencies": true,
            "Install tool dependencies": true,
        });
    });

    describe("target section", () => {
        function mountWithSections() {
            return mount(InstallationSettings, {
                propsData: {
                    repo: { name: "name", owner: "owner" },
                    changesetRevision: "changesetRevision",
                    requiresPanel: true,
                    toolshedUrl: "toolshedUrl",
                    currentPanel: { mapping: { id: "mapping", name: "Mapping", tools: ["bwa"] } },
                },
                localVue,
            });
        }

        async function pickSection(wrapper, label) {
            await wrapper.find(".multiselect__select").trigger("mousedown");
            const option = wrapper.findAll(".multiselect__option").find((element) => element.text() === label);
            await option.trigger("click");
        }

        async function install(wrapper) {
            await wrapper.find(".g-modal-confirm-buttons button:last-child").trigger("click");
            return wrapper.emitted("ok")[0][0];
        }

        it("installs into an existing section picked from the list", async () => {
            const wrapper = mountWithSections();
            await pickSection(wrapper, "Mapping");
            const request = await install(wrapper);
            expect(request.tool_panel_section_id).toBe("mapping");
            expect(request.new_tool_panel_section_label).toBe("");
        });

        it("installs into a new section typed by name", async () => {
            const wrapper = mountWithSections();
            await pickSection(wrapper, "New section...");
            await wrapper.find("#install-tool-section-other").setValue("My Tools");
            const request = await install(wrapper);
            expect(request.tool_panel_section_id).toBe("");
            expect(request.new_tool_panel_section_label).toBe("My Tools");
        });

        it("trims a new section's name", async () => {
            const wrapper = mountWithSections();
            await pickSection(wrapper, "New section...");
            await wrapper.find("#install-tool-section-other").setValue("  My Tools ");
            const request = await install(wrapper);
            expect(request.new_tool_panel_section_label).toBe("My Tools");
        });

        it("won't install into a new section whose name is blank", async () => {
            const wrapper = mountWithSections();
            await pickSection(wrapper, "New section...");
            await wrapper.find("#install-tool-section-other").setValue("   ");
            const ok = wrapper.find(".g-modal-confirm-buttons button:last-child");
            expect(ok.attributes("aria-disabled")).toBe("true");
            await ok.trigger("click");
            expect(wrapper.emitted("ok")).toBeUndefined();
        });

        it("installs outside any section by default", async () => {
            const wrapper = mountWithSections();
            const request = await install(wrapper);
            expect(request.tool_panel_section_id).toBe("");
            expect(request.new_tool_panel_section_label).toBe("");
        });

        it("won't install while a new section's name is cleared", async () => {
            const wrapper = mountWithSections();
            await pickSection(wrapper, "New section...");
            const name = wrapper.find("#install-tool-section-other");
            await name.setValue("My Tools");
            await name.setValue("");
            const ok = wrapper.find(".g-modal-confirm-buttons button:last-child");
            expect(ok.attributes("aria-disabled")).toBe("true");
            await ok.trigger("click");
            expect(wrapper.emitted("ok")).toBeUndefined();
        });

        it("asks for a name when a new section is left empty", async () => {
            const wrapper = mountWithSections();
            await pickSection(wrapper, "New section...");
            expect(wrapper.text()).toContain("Enter a value.");
        });
    });
});
