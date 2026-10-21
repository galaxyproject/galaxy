import { composeStories } from "@storybook/vue3-vite";
import { useStoryMount } from "@tests/vitest/stories";
import { describe, expect, it, onTestFinished, vi } from "vitest";

import * as stories from "./UploadMethodViewInline.stories";

import LocalFileUpload from "./methods/LocalFileUpload.vue";
import GCard from "@/components/Common/GCard.vue";

const { CollectionCreatorUpload } = composeStories(stories);
const mountStory = useStoryMount();

describe("UploadMethodViewInline", () => {
    it("renders the selected method component without making it reactive", async () => {
        const warn = vi.spyOn(console, "warn");
        onTestFinished(() => warn.mockRestore());

        const wrapper = mountStory(CollectionCreatorUpload);

        await vi.waitFor(() => expect(wrapper.findComponent(LocalFileUpload).exists()).toBe(true));
        const selectedCards = wrapper.findAllComponents(GCard).filter((card) => card.props("selected"));
        expect(selectedCards.map((card) => card.props("title"))).toEqual(["Upload from Computer"]);
        const reactiveComponentWarnings = warn.mock.calls.filter((args) =>
            String(args[0]).includes("Vue received a Component that was made a reactive object"),
        );
        expect(reactiveComponentWarnings).toEqual([]);
    });
});
