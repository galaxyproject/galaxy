import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import { sanitizeHtml } from "@/directives/sanitizeHtml";

import PageHtml from "./PageHtml.vue";

describe("PageHtml", () => {
    it("renders each top-level block of the page through v-sanitize-html with the links profile", async () => {
        vi.mocked(sanitizeHtml).mockClear();
        const wrapper = mount(PageHtml, { localVue: getLocalVue(), propsData: { page: { content: "" } } });

        await wrapper.setProps({
            page: {
                content:
                    '<div><a href="https://galaxyproject.org" target="_blank">Galaxy</a></div>' +
                    '<div class="embedded-item" id="History-abc123"></div>',
            },
        });

        const calls = vi.mocked(sanitizeHtml).mock.calls;
        expect(calls).toEqual([
            ['<a href="https://galaxyproject.org" target="_blank">Galaxy</a>', "links"],
            [expect.stringContaining("/published/history?id=abc123"), "links"],
        ]);
        expect(wrapper.findAll("p a").at(0).text()).toBe("Galaxy");
    });
});
