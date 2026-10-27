import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import axios from "axios";
import { describe, expect, it, vi } from "vitest";

import HistoryLink from "./HistoryLink.vue";

vi.mock("axios");
vi.mock("@/stores/historyStore", () => ({ useHistoryStore: () => ({ getHistoryNameById: () => "Shared history" }) }));

const localVue = getLocalVue();

function mountLink(embed: boolean) {
    return mount(HistoryLink as object, { props: { historyId: "h1" }, global: { ...localVue, provide: { embed } } });
}

describe("HistoryLink", () => {
    it("imports the history in place", async () => {
        await mountLink(false).find('[data-description="history import link"]').trigger("click");
        expect(axios.post).toHaveBeenCalledWith("/api/histories", { history_id: "h1" });
    });

    it("opens the history in Galaxy when embedded", () => {
        const link = mountLink(true).find('[data-description="history import link"]');
        expect(link.element.tagName).toBe("A");
        expect(link.attributes("href")).toBe("/histories/view?id=h1");
        expect(link.attributes("target")).toBe("_blank");
    });
});
