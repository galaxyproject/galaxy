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
        expect(links.at(1)!.attributes("href")).toBe("/galaxy/help/terms/tool");
    });

    it("rewrites gxstatic image sources and leaves other image sources alone", async () => {
        const wrapper = mount(ToolHelpMarkdown as object, {
            localVue: getLocalVue(),
            pinia: createTestingPinia({ createSpy: vi.fn }),
            propsData: {
                content: "![a](static/images/a.png) ![b](https://example.org/b.png) ![c](gxstatic://images/c.png)",
            },
            stubs: { MarkdownHelpPopovers: true },
        });
        await flushPromises();

        const srcs = wrapper.findAll("img").map((img) => img.attributes("src"));
        expect(srcs).toEqual(["static/images/a.png", "https://example.org/b.png", "/galaxy/static/images/c.png"]);
    });

    it("points relative image sources at the tool's help images", async () => {
        const wrapper = mount(ToolHelpMarkdown as object, {
            localVue: getLocalVue(),
            pinia: createTestingPinia({ createSpy: vi.fn }),
            propsData: {
                content: [
                    "![a](static/images/a.png)",
                    "![b](b%20c.png?raw=true#top)",
                    "![c](https://example.org/c.png)",
                    "![d](/static/d.png)",
                    "![e](gxstatic://images/e.png)",
                ].join(" "),
                toolId: "toolshed.g2.bx.psu.edu/repos/iuc/bedtools/slop/2.31+galaxy1",
                toolVersion: "2.31+galaxy1",
            },
            stubs: { MarkdownHelpPopovers: true },
        });
        await flushPromises();

        const srcs = wrapper.findAll("img").map((img) => img.attributes("src"));
        const helpImages = "/galaxy/api/tools/toolshed.g2.bx.psu.edu%2Frepos%2Fiuc%2Fbedtools%2Fslop%2F2.31%2Bgalaxy1";
        expect(srcs).toEqual([
            `${helpImages}/help_image?path=static%2Fimages%2Fa.png&tool_version=2.31%2Bgalaxy1`,
            `${helpImages}/help_image?path=b+c.png&tool_version=2.31%2Bgalaxy1`,
            "https://example.org/c.png",
            "/static/d.png",
            "/galaxy/static/images/e.png",
        ]);
    });
});
