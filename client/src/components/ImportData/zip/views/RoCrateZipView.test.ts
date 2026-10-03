import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { describe, expect, it, vi } from "vitest";

import { sanitizeHtml } from "@/directives/sanitizeHtml";

import RoCrateZipView from "./RoCrateZipView.vue";

const DESCRIPTION = "Crate <em>description</em> with <b>markup</b>";

vi.mock("./rocrate.utils", () => ({
    extractROCrateSummary: vi.fn(async () => ({
        name: "Example crate",
        description: DESCRIPTION,
        publicationDate: new Date("2024-01-01T00:00:00Z"),
        conformsTo: [],
        license: "CC-BY-4.0",
        creators: [],
    })),
}));

vi.mock("@/composables/zipExplorer", () => ({
    isGalaxyZipExport: () => false,
    isGalaxyHistoryExport: () => false,
}));

describe("RoCrateZipView", () => {
    it("renders the crate description through v-sanitize-html", async () => {
        setActivePinia(createPinia());
        vi.mocked(sanitizeHtml).mockImplementation((html) => `<span class="sanitized">${html}</span>`);
        const wrapper = mount(RoCrateZipView as object, {
            propsData: { explorer: { crate: {} } },
            localVue: getLocalVue(),
            stubs: { UtcDate: true },
        });
        await flushPromises();

        expect(sanitizeHtml).toHaveBeenCalledWith(DESCRIPTION, "default");
        expect(wrapper.find(".sanitized").html()).toContain("<em>description</em>");
    });
});
