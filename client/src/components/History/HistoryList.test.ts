import { createTestingPinia } from "@pinia/testing";
import { getFakeRegisteredUser } from "@tests/test-data";
import { createTestRouter, getLocalVue, suppressBootstrapVueWarnings } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { type AnyHistoryEntry, getMyHistories } from "@/api/histories";
import { useUserStore } from "@/stores/userStore";

import HistoryCard from "./HistoryCard.vue";
import HistoryList from "./HistoryList.vue";
import HistoryCardList from "@/components/History/HistoryCardList.vue";

const { confirm } = vi.hoisted(() => ({ confirm: vi.fn() }));

vi.mock("@/composables/confirmDialog", () => ({
    useConfirmDialog: () => ({ confirm }),
}));
vi.mock("@/composables/toast");
vi.mock("@/api/histories", async (importOriginal) => ({
    ...(await importOriginal<object>()),
    getMyHistories: vi.fn(),
}));

const localVue = getLocalVue();
const router = createTestRouter();

const FAKE_USER = getFakeRegisteredUser({ id: "user_id", email: "me@example.org", username: "me" });

function history(id: string, name: string, username: string): AnyHistoryEntry {
    return {
        id,
        name,
        username,
        deleted: false,
        purged: false,
        published: false,
        tags: [],
    } as unknown as AnyHistoryEntry;
}

const MINE = [history("mine_1", "Mine", "me")];

async function mountHistoryList(activeList: "my" | "shared") {
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    setActivePinia(pinia);
    useUserStore().currentUser = FAKE_USER;
    const wrapper = mount(HistoryList as object, {
        props: { activeList },
        global: { ...localVue, stubs: { ...localVue.stubs, HistoryCard: true } },
        pinia,
        router,
    });
    await flushPromises();
    return wrapper;
}

function cardList(wrapper: Awaited<ReturnType<typeof mountHistoryList>>) {
    return wrapper.findComponent(HistoryCardList);
}

async function selectAll(wrapper: Awaited<ReturnType<typeof mountHistoryList>>, histories: AnyHistoryEntry[]) {
    const cards = wrapper.findAllComponents(HistoryCard);
    for (const h of histories) {
        cards.find((card) => card.props("history").id === h.id)?.vm.$emit("select", h);
    }
    await flushPromises();
}

function deleteKeyEvent(): KeyboardEvent {
    const target = document.createElement("div");
    target.classList.add("history-card-in-list");
    return { key: "Delete", shiftKey: false, target, preventDefault: () => {} } as unknown as KeyboardEvent;
}

describe("HistoryList", () => {
    beforeEach(() => {
        suppressBootstrapVueWarnings();
        vi.clearAllMocks();
        vi.mocked(getMyHistories).mockResolvedValue({ data: MINE, total: 1 } as never);
    });

    it("keeps the owner bulk actions in my view", async () => {
        const wrapper = await mountHistoryList("my");
        await selectAll(wrapper, MINE);

        expect(wrapper.find("#history-list-footer-bulk-delete-button").exists()).toBe(true);
    });

    it("asks to delete on the Delete key in my view", async () => {
        confirm.mockResolvedValue(false);
        const wrapper = await mountHistoryList("my");

        cardList(wrapper).vm.$emit("on-key-down", MINE[0], deleteKeyEvent());
        await flushPromises();

        expect(confirm).toHaveBeenCalledTimes(1);
        expect(confirm.mock.calls[0]?.[1]).toMatchObject({ title: "Delete History" });
    });
});
