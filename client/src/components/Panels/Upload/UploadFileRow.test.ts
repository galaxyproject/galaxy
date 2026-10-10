import { composeStories } from "@storybook/vue3-vite";
import { useStoryMount } from "@tests/vitest/stories";
import { describe, expect, it } from "vitest";

import * as UploadFileRowStories from "./UploadFileRow.stories";

import CopyToClipboard from "@/components/CopyToClipboard.vue";

const { LinkQueued, FileUploading } = composeStories(UploadFileRowStories);
const mountStory = useStoryMount();

const LINK = "https://zenodo.org/records/582600/files/mutant_R1.fastq";

describe("UploadFileRow source URL", () => {
    it("renders the source URL from the item display info", () => {
        const wrapper = mountStory(LinkQueued);

        const url = wrapper.find(".source-url-text");
        expect(url.exists()).toBe(true);
        expect(url.text()).toContain(LINK);
        expect(url.attributes("title")).toBe(LINK);

        const copyIcon = wrapper.findComponent(CopyToClipboard);
        expect(copyIcon.exists()).toBe(true);
        expect(copyIcon.props("text")).toBe(LINK);
    });

    it("shows no source URL for a file from the user's computer", () => {
        const wrapper = mountStory(FileUploading);

        expect(wrapper.find(".source-url").exists()).toBe(false);
        expect(wrapper.findComponent(CopyToClipboard).exists()).toBe(false);
    });
});
