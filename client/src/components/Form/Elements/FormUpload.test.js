import { composeStories } from "@storybook/vue3-vite";
import { useStoryMount } from "@tests/vitest/stories";
import { describe, expect, it } from "vitest";

import * as FormUploadStories from "./FormUpload.stories";

const stories = composeStories(FormUploadStories);
const mountStory = useStoryMount();

describe("FormUpload", () => {
    it("should not display text box if file has not been selected", () => {
        const wrapper = mountStory(stories.NoFileChosen);
        const textarea = wrapper.get("textarea");
        // happy-dom's getComputedStyle doesn't reflect inline styles reliably, so
        // isVisible() (which relies on it) can't be used here -- check the v-show
        // style directly instead.
        expect(textarea.element.style.display).toBe("none");
        expect(textarea.text()).toBe("");
        // Native textarea contents live in value; empty textContent alone cannot prove they are empty.
        expect(textarea.element.value).toBe("");
        const noInput = wrapper.get("label");
        expect(noInput.text()).toBe("No file chosen");
    });
});
