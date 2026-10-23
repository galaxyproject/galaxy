import "@/composables/__mocks__/filter";

import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import InstallationSettings from "./InstallationSettings.vue";

vi.mock("app");
// Mock the useConfig composable
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

describe("InstallationSettings", () => {
    beforeEach(() => {
        server.use(
            http.get("/api/configuration/dynamic_tool_confs", ({ response }) => {
                return response(200).json([]);
            }),
        );
    });

    it("installs with the tool configuration picked from a named radio group", async () => {
        server.use(
            http.get("/api/configuration/dynamic_tool_confs", ({ response }) => {
                return response(200).json([
                    { config_filename: "first_conf.xml" },
                    { config_filename: "second_conf.xml" },
                ]);
            }),
        );
        const wrapper = mount(InstallationSettings, {
            props: {
                repo: { name: "name", owner: "owner" },
                changesetRevision: "changesetRevision",
                requiresPanel: false,
                toolshedUrl: "toolshedUrl",
            },
            global: localVue,
        });
        await vi.waitFor(() => expect(wrapper.findAll("input[type=radio]").length).toBe(2));
        const group = wrapper.find("[role=radiogroup]");
        expect(wrapper.get(`#${group.attributes("aria-labelledby")}`).text()).toBe("Tool Configuration:");
        expect(group.find("legend").text()).toBe("Tool Configuration:");
        expect(group.element.parentElement.closest("fieldset")).toBeNull();
        expect(wrapper.get(`#${group.attributes("aria-describedby")}`).text()).toBe("Choose a tool configuration.");
        const radios = group.findAll("input[type=radio]");
        expect(radios.map((radio) => radio.attributes("value"))).toEqual(["first_conf.xml", "second_conf.xml"]);
        expect(radios[0].element.checked).toBe(true);
        expect(new Set(radios.map((radio) => radio.attributes("name"))).size).toBe(1);
        await radios[1].setValue(true);
        await wrapper.find(".g-modal-confirm-buttons button:last-child").trigger("click");
        expect(wrapper.emitted("ok")[0][0].shed_tool_conf).toBe("second_conf.xml");
    });

    it("test tool repository installer interface", () => {
        const wrapper = mount(InstallationSettings, {
            propsData: {
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
        expect(wrapper.find(".g-modal-title").text()).toBe("Installing 'name'");
        expect(wrapper.find(".description").text()).toBe("long_description");
        expect(wrapper.find(".revision").text()).toBe("owner rev. changesetRevision");

        const sectionInput = wrapper.get("#install-tool-section");
        expect(wrapper.get('label[for="install-tool-section"]').text()).toBe("Target Section:");
        expect(sectionInput.element.closest('[role="combobox"]')).not.toBeNull();

        expect(wrapper.vm.installToolDependencies).toBe(true);
        expect(wrapper.vm.installRepositoryDependencies).toBe(true);
        expect(wrapper.vm.installResolverDependencies).toBe(true);
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
