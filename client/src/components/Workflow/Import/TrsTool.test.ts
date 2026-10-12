import { getLocalVue, nth } from "@tests/vitest/helpers";
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { sanitizeHtml } from "@/directives/sanitizeHtml";

import type { TrsTool as TrsToolData } from "./types";

import TrsTool from "./TrsTool.vue";

const registryTool = {
    id: "#workflow/example",
    name: "example",
    description: "A [workflow](https://example.org) with <b>markup</b>",
    organization: "org",
    versions: [{ id: "v1", name: "v1" }],
} satisfies TrsToolData;

const sanitizeSpy = vi.mocked(sanitizeHtml);
const originalSanitizeImplementation = sanitizeSpy.getMockImplementation();

beforeEach(() => {
    sanitizeSpy.mockClear();
    sanitizeSpy.mockImplementation((html) => `<span class="sanitized">${html}</span>`);
});

afterEach(() => {
    sanitizeSpy.mockReset();
    if (originalSanitizeImplementation) {
        sanitizeSpy.mockImplementation(originalSanitizeImplementation);
    }
});
// Vitest runs afterEach hooks in reverse order: unmount while the test's
// sanitizer implementation is still installed, then restore the shared spy.
enableAutoUnmount(afterEach);

describe("TrsTool", () => {
    it("renders the registry description through v-sanitize-html with the links profile", () => {
        const wrapper = mount(TrsTool, {
            global: getLocalVue(),
            props: { trsTool: registryTool },
        });

        expect(sanitizeSpy).toHaveBeenCalledTimes(1);
        const [html, profile] = nth(sanitizeSpy.mock.calls, -1);
        expect(profile).toBe("links");
        expect(html).toContain('<a href="https://example.org" target="_blank">workflow</a>');
        expect(html).toContain("&lt;b&gt;markup&lt;/b&gt;");
        expect(wrapper.find(".sanitized").exists()).toBe(true);
    });

    it("lists versions newest first and emits the picked version", async () => {
        const versions = [
            { id: "id-1", name: "1.0" },
            { id: "id-2", name: "2.0" },
        ];
        const wrapper = mount(TrsTool, {
            global: getLocalVue(),
            props: { trsTool: { ...registryTool, description: "", versions } },
        });
        const select = wrapper.get(".workflow-version-select");

        expect(select.attributes("aria-label")).toBe("Select a version");
        expect(select.findAll("option").map((option) => option.text())).toEqual(["2.0", "1.0"]);
        expect(wrapper.emitted("onSelect")).toEqual([["id-2"]]);

        (select.element as HTMLSelectElement).options[1]!.selected = true;
        await select.trigger("change");
        await flushPromises();

        expect(wrapper.emitted("onSelect")).toEqual([["id-2"], ["id-1"]]);
    });
});
