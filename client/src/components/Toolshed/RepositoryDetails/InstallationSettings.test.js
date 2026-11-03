import "@/composables/__mocks__/filter";

import { composeStories } from "@storybook/vue3-vite";
import { emittedArg, nth } from "@tests/vitest/helpers";
import { useStoryMount } from "@tests/vitest/stories";
import { describe, expect, it, vi } from "vitest";

import * as InstallationSettingsStories from "./InstallationSettings.stories";

import InstallationSettings from "./InstallationSettings.vue";

const { ChecksEachConfiguredDependency, SeveralToolConfigs, WithToolPanel } =
    composeStories(InstallationSettingsStories);
const mountStory = useStoryMount();

async function install(wrapper) {
    await wrapper.find(".g-modal-confirm-buttons button:last-child").trigger("click");
    return emittedArg(wrapper, "ok");
}

// Display and dependency defaults are exercised by the browser plays.
describe("InstallationSettings", () => {
    it("installs with the tool configuration picked from a named radio group", async () => {
        const wrapper = mountStory(SeveralToolConfigs).getComponent(InstallationSettings);
        await vi.waitFor(() => expect(wrapper.findAll("input[type=radio]").length).toBe(2));
        const group = wrapper.find("[role=radiogroup]");
        expect(wrapper.get(`#${group.attributes("aria-labelledby")}`).text()).toBe("Tool Configuration:");
        expect(group.element.parentElement.closest("fieldset")).toBeNull();
        expect(wrapper.get(`#${group.attributes("aria-describedby")}`).text()).toBe("Choose a tool configuration.");
        const radios = group.findAll("input[type=radio]");
        expect(radios.map((radio) => radio.attributes("value"))).toEqual([
            "shed_tool_conf.xml",
            "custom_shed_tool_conf.xml",
        ]);
        expect(nth(radios, 0).element.checked).toBe(true);
        expect(new Set(radios.map((radio) => radio.attributes("name"))).size).toBe(1);
        await nth(radios, 1).setValue(true);
        const request = await install(wrapper);
        expect(request.shed_tool_conf).toBe("custom_shed_tool_conf.xml");
    });

    it("installs with the dependency choices made in the labelled checkboxes", async () => {
        const wrapper = mountStory(ChecksEachConfiguredDependency).getComponent(InstallationSettings);
        const checkboxes = wrapper.findAll("input[type=checkbox]");
        expect(checkboxes.map((checkbox) => checkbox.element.closest("label")?.textContent.trim())).toEqual([
            "Install resolvable dependencies",
            "Install repository dependencies",
            "Install tool dependencies",
        ]);
        expect(checkboxes.map((checkbox) => checkbox.element.checked)).toEqual([false, true, true]);
        await nth(checkboxes, 2).setValue(false);
        const request = await install(wrapper);
        expect(request.install_resolver_dependencies).toBe(false);
        expect(request.install_repository_dependencies).toBe(true);
        expect(request.install_tool_dependencies).toBe(false);
    });

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
