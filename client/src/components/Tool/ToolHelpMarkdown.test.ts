import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import { sanitizeHtml } from "@/directives/sanitizeHtml";

import ToolHelpMarkdown from "./ToolHelpMarkdown.vue";

vi.mock("@/onload/loadConfig", () => ({ getAppRoot: () => "/galaxy/" }));

describe("ToolHelpMarkdown", () => {
    it("renders help through v-sanitize-html with the markdown profile", async () => {
        vi.mocked(sanitizeHtml).mockClear();
        const wrapper = mount(ToolHelpMarkdown as object, {
            localVue: getLocalVue(),
            pinia: createTestingPinia({ createSpy: vi.fn }),
            propsData: { content: "See [docs](https://example.org), a [term](gxhelp://tool) and <b>raw</b>" },
            stubs: { MarkdownHelpPopovers: true },
        });
        await flushPromises();

        const [html, profile] = vi.mocked(sanitizeHtml).mock.calls[0]!;
        expect(profile).toBe("markdown");
        expect(html).toContain('href="https://example.org" target="_blank"');
        expect(html).toContain("&lt;b&gt;raw&lt;/b&gt;");
        const links = wrapper.findAll("a");
        expect(links.at(1).attributes("href")).toBe("/galaxy/help/terms/tool");
    });
});
