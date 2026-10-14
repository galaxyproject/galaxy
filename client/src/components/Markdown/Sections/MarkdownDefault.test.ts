import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import { sanitizeHtml } from "@/directives/sanitizeHtml";

import MarkdownDefault from "./MarkdownDefault.vue";

vi.mock("@/onload/loadConfig", () => ({ getAppRoot: () => "/galaxy/" }));

describe("MarkdownDefault", () => {
    it("renders through v-sanitize-html with the markdown profile and still rewrites gx links", async () => {
        vi.mocked(sanitizeHtml).mockClear();
        const wrapper = mount(MarkdownDefault as object, {
            localVue: getLocalVue(),
            pinia: createTestingPinia({ createSpy: vi.fn }),
            propsData: { content: "See [a term](gxhelp://dataset) and <em>raw</em>" },
            stubs: { MarkdownHelpPopovers: true },
        });
        await flushPromises();

        const [html, profile] = vi.mocked(sanitizeHtml).mock.calls[0]!;
        expect(profile).toBe("markdown");
        expect(html).toContain('<a href="gxhelp://dataset">a term</a>');
        expect(html).toContain("&lt;em&gt;raw&lt;/em&gt;");
        expect(wrapper.find(".text-justify a").attributes("href")).toBe("/galaxy/help/terms/dataset");
    });
});
