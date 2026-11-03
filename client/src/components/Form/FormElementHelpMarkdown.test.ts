import { getLocalVue, nth } from "@tests/vitest/helpers";
import { enableAutoUnmount, shallowMount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import { sanitizeHtml } from "@/directives/sanitizeHtml";

import FormElementHelpMarkdown from "./FormElementHelpMarkdown.vue";

vi.mock("@/onload/loadConfig", () => ({ getAppRoot: () => "/galaxy/" }));

describe("FormElementHelpMarkdown", () => {
    afterEach(() => {
        vi.mocked(sanitizeHtml).mockClear();
    });
    enableAutoUnmount(afterEach);

    it("renders help through v-sanitize-html with the markdown profile and keeps gxhelp links working", () => {
        vi.mocked(sanitizeHtml).mockClear();
        const wrapper = shallowMount(FormElementHelpMarkdown, {
            global: getLocalVue(),
            props: { content: "A [dataset](gxhelp://dataset) and <b>raw</b>" },
        });

        const [html, profile] = nth(vi.mocked(sanitizeHtml).mock.calls, 0);
        expect(profile).toBe("markdown");
        expect(html).toContain('<a href="gxhelp://dataset">dataset</a>');
        expect(html).toContain("&lt;b&gt;raw&lt;/b&gt;");
        expect(wrapper.get("a").attributes("href")).toBe("/galaxy/help/terms/dataset");
    });
});
