import { composeStories } from "@storybook/vue3-vite";
import { useStoryMount } from "@tests/vitest/stories";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { sanitizeHtml } from "@/directives/sanitizeHtml";

import * as PermissionsInputFieldStories from "./PermissionsInputField.stories";

const { NoRolesChosen } = composeStories(PermissionsInputFieldStories);
const mountStory = useStoryMount();

describe("PermissionsInputField", () => {
    beforeEach(() => {
        vi.mocked(sanitizeHtml).mockClear();
    });

    it("sends the alert through v-sanitize-html's default profile", () => {
        mountStory(NoRolesChosen);

        expect(sanitizeHtml).toHaveBeenCalledWith(NoRolesChosen.args.alert, "default");
    });
});
