import { composeStories } from "@storybook/vue3-vite";
import { useStoryMount } from "@tests/vitest/stories";
import { describe, expect, it } from "vitest";

import * as ExportFormStories from "./ExportForm.stories";

const stories = composeStories(ExportFormStories);
const mountStory = useStoryMount();

// The repository prompt, filling the form, enabling and clicking Export, and clearing after export are covered by the play functions.
describe("ExportForm.vue", () => {
    it("localizes the export button text", () => {
        const wrapper = mountStory(stories.HistoryArchive, { instrumentLocalization: true });

        expect(wrapper.get(".export-button").text()).toBeLocalizationOf("Export");
    });
});
