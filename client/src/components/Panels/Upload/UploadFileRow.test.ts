import { composeStories } from "@storybook/vue3-vite";
import { useStoryMount } from "@tests/vitest/stories";
import { describe, expect, it } from "vitest";

import * as UploadFileRowStories from "./UploadFileRow.stories";

import CopyToClipboard from "@/components/CopyToClipboard.vue";

const { LinkQueued } = composeStories(UploadFileRowStories);
const mountStory = useStoryMount();

const LINK = "https://zenodo.org/records/582600/files/mutant_R1.fastq";

describe("UploadFileRow source URL", () => {
    it("offers to copy the source URL", () => {
        const wrapper = mountStory(LinkQueued);

        // Clicking the copy icon does nothing in the browser (BUGS_FOUND), so a play can't show what it copies.
        const copyIcon = wrapper.findComponent(CopyToClipboard);
        expect(copyIcon.exists()).toBe(true);
        expect(copyIcon.props("text")).toBe(LINK);
    });
});
