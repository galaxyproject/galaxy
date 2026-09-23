import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import { sanitizeHtml } from "@/directives/sanitizeHtml";

import TrsTool from "./TrsTool.vue";

describe("TrsTool", () => {
    it("renders the registry description through v-sanitize-html with the links profile", () => {
        vi.mocked(sanitizeHtml).mockImplementation((html) => `<span class="sanitized">${html}</span>`);
        const wrapper = mount(TrsTool as object, {
            localVue: getLocalVue(),
            propsData: {
                trsTool: {
                    id: "#workflow/example",
                    name: "example",
                    description: "A [workflow](https://example.org) with <b>markup</b>",
                    organization: "org",
                    versions: [{ id: "v1", name: "v1" }],
                },
            },
        });

        const [html, profile] = vi.mocked(sanitizeHtml).mock.calls.at(-1)!;
        expect(profile).toBe("links");
        expect(html).toContain('<a href="https://example.org" target="_blank">workflow</a>');
        expect(html).toContain("&lt;b&gt;markup&lt;/b&gt;");
        expect(wrapper.find(".sanitized").exists()).toBe(true);
    });
});
