import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import CardDownloadWorkbook from "./CardDownloadWorkbook.vue";

const DOWNLOAD_LINK = '[data-description="workbook download link"]';

describe("CardDownloadWorkbook", () => {
    it("renders a button that emits download when no link is given", async () => {
        const wrapper = mount(CardDownloadWorkbook as object, { global: getLocalVue() });
        const link = wrapper.get(DOWNLOAD_LINK);
        expect(link.element.tagName).toBe("BUTTON");
        await link.trigger("click");
        expect(wrapper.emitted("download")).toHaveLength(1);
    });

    it("renders an anchor to the workbook link when one is given", () => {
        const wrapper = mount(CardDownloadWorkbook as object, {
            props: { generateWorkbookLink: "/api/workbook" },
            global: getLocalVue(),
        });
        const link = wrapper.get(DOWNLOAD_LINK);
        expect(link.element.tagName).toBe("A");
        expect(link.attributes("href")).toBe("/api/workbook");
    });
});
