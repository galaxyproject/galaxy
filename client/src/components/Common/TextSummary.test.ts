import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import { sanitizeHtml } from "@/directives/sanitizeHtml";

import TextSummary from "./TextSummary.vue";

const DESCRIPTION = "Trimmed <b>paired</b> reads";

enableAutoUnmount(afterEach);

function mountSummary(props: Pick<InstanceType<typeof TextSummary>["$props"], "description" | "isHtml">) {
    return mount(TextSummary, { global: getLocalVue(), props });
}

describe("TextSummary", () => {
    it("renders the description as text by default", () => {
        vi.mocked(sanitizeHtml).mockClear();
        const paragraph = mountSummary({ description: DESCRIPTION }).get(".html-paragraph");

        expect(paragraph.find("b").exists()).toBe(false);
        expect(paragraph.text()).toBe(DESCRIPTION);
        expect(sanitizeHtml).not.toHaveBeenCalled();
    });

    it("renders the description through v-sanitize-html when isHtml is set", () => {
        vi.mocked(sanitizeHtml).mockClear();
        const paragraph = mountSummary({ description: DESCRIPTION, isHtml: true }).get(".html-paragraph");

        expect(sanitizeHtml).toHaveBeenCalledWith(DESCRIPTION, "default");
        expect(paragraph.get("b").text()).toBe("paired");
    });
});
