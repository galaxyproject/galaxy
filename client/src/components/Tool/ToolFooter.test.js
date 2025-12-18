import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ToolFooter from "./ToolFooter.vue";

const localVue = getLocalVue(true);

const citationsA = [
    {
        raw: "@misc{entry_a, year = {1111}}",
        cite: {
            format: vi.fn(
                () =>
                    '<div class="csl-bib-body"><div data-csl-entry-id="entry_a" class="csl-entry">Entry A (1111)</div></div>',
            ),
            data: [{ URL: "https://example.com/a" }],
        },
    },
];

const citationsB = [
    {
        raw: "@misc{entry_b, year = {2222}}",
        cite: {
            format: vi.fn(
                () =>
                    '<div class="csl-bib-body"><div data-csl-entry-id="entry_b" class="csl-entry">Entry B (2222)</div></div>',
            ),
            data: [{ URL: "https://example.com/b" }],
        },
    },
];

vi.mock("@/components/Citation/services", () => ({
    getCitations: vi.fn((source, id) => {
        if (id === "tool_a") {
            return Promise.resolve(citationsA);
        } else if (id === "tool_b") {
            return Promise.resolve(citationsB);
        }
        return Promise.resolve([]);
    }),
}));

describe("ToolFooter", () => {
    let wrapper;

    beforeEach(() => {
        wrapper = mount(ToolFooter, {
            propsData: {
                id: "tool_a",
                hasCitations: true,
                xrefs: [],
                license: "tool_license",
                creators: [],
                requirements: [],
            },
            localVue,
            stubs: {
                CitationItem: false,
                License: true,
                Creators: true,
                FontAwesomeIcon: true,
            },
        });
    });

    it("check props", async () => {
        await flushPromises();
        expect(wrapper.findAll(".footer-section-name").at(0).text()).toBeLocalizationOf("References");
        const referenceA = wrapper.find(".formatted-reference .csl-entry");
        expect(referenceA.attributes()["data-csl-entry-id"]).toBe("entry_a");
        expect(referenceA.text()).toContain("1111");
        await wrapper.setProps({ id: "tool_b" });
        await flushPromises();
        const referenceB = wrapper.find(".formatted-reference .csl-entry");
        expect(referenceB.attributes()["data-csl-entry-id"]).toBe("entry_b");
        expect(referenceB.text()).toContain("2222");
    });
});
