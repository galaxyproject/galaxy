import { composeStories } from "@storybook/vue3-vite";
import { useStoryMount } from "@tests/vitest/stories";
import { describe, expect, it } from "vitest";

import * as ExportFormStories from "./ExportForm.stories";

import ExportForm from "./ExportForm.vue";
import FilesInput from "@/components/FilesDialog/FilesInput.vue";

const stories = composeStories(ExportFormStories);
const mountStory = useStoryMount();

const EXPORT_BUTTON = ".export-button";
const NAME_INPUT = "#name";
const DIRECTORY_DESCRIPTION = "#fieldset-directory .form-text";

const NAME = "export.tar.gz";
const DIRECTORY = "gxfiles://";

type ExportFormWrapper = ReturnType<typeof mountExportForm>;

function mountExportForm(props: { clearInputAfterExport?: boolean } = {}) {
    return mountStory(stories.HistoryArchive, { props, instrumentLocalization: true }).findComponent(ExportForm);
}

async function fillInputs(wrapper: ExportFormWrapper, inputs: { name?: string; directory?: string }) {
    if (inputs.name !== undefined) {
        await wrapper.get(NAME_INPUT).setValue(inputs.name);
    }
    if (inputs.directory !== undefined) {
        await wrapper.getComponent(FilesInput).vm.$emit("input", inputs.directory);
    }
}

function exportButtonAriaDisabled(wrapper: ExportFormWrapper) {
    return wrapper.get(EXPORT_BUTTON).attributes("aria-disabled");
}

describe("ExportForm.vue", () => {
    it.each([
        { story: stories.HistoryArchive, what: "history archive" },
        { story: stories.History, what: "history" },
    ])("asks for a repository to export the $what to", ({ story, what }) => {
        const wrapper = mountStory(story);

        expect(wrapper.get(DIRECTORY_DESCRIPTION).text()).toBe(`Select a 'repository' to export ${what} to.`);
    });

    it.each([
        { missing: "both inputs are", inputs: {} },
        { missing: "the directory is", inputs: { name: NAME } },
        { missing: "the name is", inputs: { directory: DIRECTORY } },
    ])("disables export when $missing empty", async ({ inputs }) => {
        const wrapper = mountExportForm();

        await fillInputs(wrapper, inputs);

        expect(exportButtonAriaDisabled(wrapper)).toBe("true");
    });

    it("enables export when the name and directory are both set", async () => {
        const wrapper = mountExportForm();

        await fillInputs(wrapper, { name: NAME, directory: DIRECTORY });

        expect(exportButtonAriaDisabled(wrapper)).toBeUndefined();
    });

    it("localizes the export button text", () => {
        const wrapper = mountExportForm();

        expect(wrapper.get(EXPORT_BUTTON).text()).toBeLocalizationOf("Export");
    });

    it("emits the directory and name when export is clicked", async () => {
        const wrapper = mountExportForm();
        await fillInputs(wrapper, { name: NAME, directory: DIRECTORY });
        expect(wrapper.emitted("export")).toBeUndefined();

        await wrapper.get(EXPORT_BUTTON).trigger("click");

        expect(wrapper.emitted("export")).toEqual([[DIRECTORY, NAME]]);
    });

    it("clears the inputs, disabling export, after export when clearInputAfterExport is set", async () => {
        const wrapper = mountExportForm({ clearInputAfterExport: true });
        await fillInputs(wrapper, { name: NAME, directory: DIRECTORY });

        await wrapper.get(EXPORT_BUTTON).trigger("click");

        expect(wrapper.emitted("export")).toEqual([[DIRECTORY, NAME]]);
        expect((wrapper.get(NAME_INPUT).element as HTMLInputElement).value).toBe("");
        expect(wrapper.getComponent(FilesInput).props("value")).toBe("");
        expect(exportButtonAriaDisabled(wrapper)).toBe("true");
    });
});
