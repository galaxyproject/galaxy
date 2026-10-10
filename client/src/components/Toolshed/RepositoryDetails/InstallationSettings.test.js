import "@/composables/__mocks__/filter";

import { composeStories } from "@storybook/vue3-vite";
import { useStoryMount } from "@tests/vitest/stories";
import { describe, expect, it } from "vitest";

import * as InstallationSettingsStories from "./InstallationSettings.stories";

import InstallationSettings from "./InstallationSettings.vue";

const { WithToolPanel } = composeStories(InstallationSettingsStories);
const mountStory = useStoryMount();

// Display and dependency defaults are exercised by the browser plays.
describe("InstallationSettings", () => {
    describe("target section", () => {
        function mountWithSections() {
            return mountStory(WithToolPanel, {
                props: {
                    currentPanel: { mapping: { id: "mapping", name: "Mapping", tools: ["bwa"] } },
                },
            }).getComponent(InstallationSettings);
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
