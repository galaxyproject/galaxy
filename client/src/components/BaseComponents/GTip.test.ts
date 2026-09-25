import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import { sanitizeHtml } from "@/directives/sanitizeHtml";

import GTip from "./GTip.vue";

describe("GTip", () => {
    it("renders the tip markdown through v-sanitize-html with the links profile", () => {
        vi.mocked(sanitizeHtml).mockClear();
        const wrapper = mount(GTip as object, {
            localVue: getLocalVue(),
            propsData: { tips: ["Read the **docs** at [Galaxy](https://galaxyproject.org)"] },
        });

        const [html, profile] = vi.mocked(sanitizeHtml).mock.calls[0]!;
        expect(profile).toBe("links");
        expect(html).toContain("<strong>docs</strong>");
        expect(html).toContain('href="https://galaxyproject.org" target="_blank"');
        expect(wrapper.find(".tip-item span").element.querySelector("strong")?.textContent).toBe("docs");
    });
});
