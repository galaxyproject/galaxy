import { getLocalVue, nth } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { StoredWorkflowDetailed } from "@/api/workflows";
import { sanitizeHtml } from "@/directives/sanitizeHtml";

import WorkflowHelpDisplay from "./WorkflowHelpDisplay.vue";

const localVue = getLocalVue();

describe("WorkflowHelpDisplay", () => {
    beforeEach(() => {
        vi.mocked(sanitizeHtml).mockClear();
        vi.mocked(sanitizeHtml).mockImplementation((html) => `<span class="sanitized">${html}</span>`);
    });

    it("renders readme and help markdown through v-sanitize-html with the links profile", () => {
        const workflow: Pick<StoredWorkflowDetailed, "readme" | "help"> = {
            readme: "**Readme** with [a link](https://galaxyproject.org) and <em>raw</em>",
            help: "Help *text*",
        };
        const wrapper = mount(WorkflowHelpDisplay, {
            global: localVue,
            props: {
                // The original rendering fixture omits workflow identity, steps and sharing metadata.
                workflow: workflow as StoredWorkflowDetailed,
            },
        });

        const calls = vi.mocked(sanitizeHtml).mock.calls;
        expect(calls).toHaveLength(2);
        const [readmeHtml, readmeProfile] = nth(calls, 0);
        expect(readmeProfile).toBe("links");
        expect(readmeHtml).toContain("<strong>Readme</strong>");
        expect(readmeHtml).toContain('target="_blank"');
        expect(readmeHtml).toContain("&lt;em&gt;raw&lt;/em&gt;");
        expect(nth(calls, 1)[1]).toBe("links");

        const rendered = wrapper.findAll(".container .sanitized");
        expect(rendered).toHaveLength(2);
        expect(nth(rendered, 1).html()).toContain("<em>text</em>");
    });
});
