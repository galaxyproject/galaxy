import { getLocalVue } from "@tests/vitest/helpers";
import { flushPromises, mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import { sanitizeHtml } from "@/directives/sanitizeHtml";

import TrsTool from "./TrsTool.vue";

describe("TrsTool", () => {
    it("renders the registry description through v-sanitize-html with the links profile", () => {
        vi.mocked(sanitizeHtml).mockImplementation((html) => `<span class="sanitized">${html}</span>`);
        const wrapper = mount(TrsTool as object, {
            global: getLocalVue(),
            props: {
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

    it("lists versions newest first and emits the picked version", async () => {
        const wrapper = mount(TrsTool as object, {
            global: getLocalVue(),
            props: {
                trsTool: {
                    id: "#workflow/example",
                    name: "example",
                    description: "",
                    organization: "org",
                    versions: [
                        { id: "id-1", name: "1.0" },
                        { id: "id-2", name: "2.0" },
                    ],
                },
            },
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
