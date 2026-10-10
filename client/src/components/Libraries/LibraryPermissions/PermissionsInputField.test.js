import { composeStories } from "@storybook/vue3-vite";
import { useStoryMount } from "@tests/vitest/stories";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { sanitizeHtml } from "@/directives/sanitizeHtml";

import * as PermissionsInputFieldStories from "./PermissionsInputField.stories";

import GAlert from "@/components/BaseComponents/GAlert.vue";

const { NoRolesChosen } = composeStories(PermissionsInputFieldStories);
const mountStory = useStoryMount();

describe("PermissionsInputField", () => {
    beforeEach(() => {
        vi.mocked(sanitizeHtml).mockClear();
    });

    it("renders the alert through v-sanitize-html", () => {
        const wrapper = mountStory(NoRolesChosen);

        expect(sanitizeHtml).toHaveBeenCalledWith(NoRolesChosen.args.alert, "default");
        expect(wrapper.findComponent(GAlert).find("strong").text()).toBe("any");
    });
});
