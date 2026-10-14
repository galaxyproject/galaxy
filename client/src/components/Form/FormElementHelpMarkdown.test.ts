import { composeStories } from "@storybook/vue3-vite";
import { nth } from "@tests/vitest/helpers";
import { useStoryMount } from "@tests/vitest/stories";
import { afterEach, describe, expect, it, vi } from "vitest";

import { sanitizeHtml } from "@/directives/sanitizeHtml";

import * as FormElementHelpMarkdownStories from "./FormElementHelpMarkdown.stories";

const stories = composeStories(FormElementHelpMarkdownStories);
const mountStory = useStoryMount();

vi.mock("@/onload/loadConfig", () => ({ getAppRoot: () => "/galaxy/" }));

describe("FormElementHelpMarkdown", () => {
    afterEach(() => {
        vi.mocked(sanitizeHtml).mockClear();
    });

    it("renders help through v-sanitize-html with the markdown profile and keeps gxhelp links working", () => {
        vi.mocked(sanitizeHtml).mockClear();
        const wrapper = mountStory(stories.RegularExpressionHelp);

        const [html, profile] = nth(vi.mocked(sanitizeHtml).mock.calls, 0);
        expect(profile).toBe("markdown");
        expect(html).toContain('<a href="gxhelp://programming.python.regex">regular expression</a>');
        expect(html).toContain("&lt;b&gt;raw&lt;/b&gt;");
        expect(wrapper.get("a").attributes("href")).toBe("/galaxy/help/terms/programming.python.regex");
    });
});
