import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import { sanitizeHtml } from "@/directives/sanitizeHtml";

import TextSummary from "./TextSummary.vue";

const DESCRIPTION = "Trimmed <b>paired</b> reads";

function mountSummary(propsData: Record<string, unknown>) {
    return mount(TextSummary as object, { localVue: getLocalVue(), propsData });
}

describe("TextSummary", () => {
    it("renders the description as text by default", () => {
        vi.mocked(sanitizeHtml).mockClear();
        const paragraph = mountSummary({ description: DESCRIPTION }).find(".html-paragraph");

        expect(paragraph.find("b").exists()).toBe(false);
        expect(paragraph.text()).toBe(DESCRIPTION);
        expect(sanitizeHtml).not.toHaveBeenCalled();
    });

    it("renders the description through v-sanitize-html when isHtml is set", () => {
        vi.mocked(sanitizeHtml).mockClear();
        const paragraph = mountSummary({ description: DESCRIPTION, isHtml: true }).find(".html-paragraph");

        expect(sanitizeHtml).toHaveBeenCalledWith(DESCRIPTION, "default");
        expect(paragraph.find("b").text()).toBe("paired");
    });
});
