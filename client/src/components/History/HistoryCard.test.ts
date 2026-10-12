import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import type { RegisteredUser } from "@/api";
import type { AnyHistoryEntry } from "@/api/histories";
import { useUserStore } from "@/stores/userStore";

import HistoryCard from "./HistoryCard.vue";

vi.mock("@/composables/confirmDialog", () => ({
    useConfirmDialog: () => ({ confirm: vi.fn() }),
}));

const OWNER = "owner";
const HISTORY_NAME = "Differential expression of liver samples, batch 2, trimmed and aligned to GRCh38";

function mountOwnHistoryCard() {
    const localVue = getLocalVue();
    useUserStore().setCurrentUser({ id: "user_id", email: "owner@example.org", username: OWNER } as RegisteredUser);
    const history = {
        id: "history_id",
        name: HISTORY_NAME,
        username: OWNER,
        deleted: false,
        purged: false,
        tags: [],
        count: 3,
        update_time: "2026-01-01T00:00:00",
    } as unknown as AnyHistoryEntry;
    return mount(HistoryCard as object, {
        props: { history },
        global: {
            ...localVue,
            stubs: { ...localVue.stubs, FontAwesomeIcon: true, HistoryDatasetsBadge: true },
        },
    });
}

describe("HistoryCard", () => {
    it("shows the name of an owned history as plain text, not as a link", () => {
        const wrapper = mountOwnHistoryCard();

        expect(wrapper.find("#g-card-title-link-history-history_id").exists()).toBe(false);
        const title = wrapper.find("#g-card-title-text-history-history_id");
        expect(title.text()).toBe(HISTORY_NAME);
        expect(title.element.tagName).toBe("SPAN");
        expect(title.attributes("title")).toBe(HISTORY_NAME);
    });
});
