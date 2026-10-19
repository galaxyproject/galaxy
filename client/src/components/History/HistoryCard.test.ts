import { deferred } from "@tests/vitest/deferred";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { reactive } from "vue";

import type { RegisteredUser } from "@/api";
import type { AnyHistoryEntry } from "@/api/histories";
import { Toast } from "@/composables/toast";
import { updateHistoryFields } from "@/stores/services/history.services";
import { useUserStore } from "@/stores/userStore";

import HistoryCard from "./HistoryCard.vue";
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";

vi.mock("@/composables/confirmDialog", () => ({
    useConfirmDialog: () => ({ confirm: vi.fn() }),
}));

vi.mock("@/composables/toast");

vi.mock("@/stores/services/history.services", async (importOriginal) => ({
    ...(await importOriginal<object>()),
    updateHistoryFields: vi.fn(),
}));

const mockedUpdateHistoryFields = vi.mocked(updateHistoryFields);

const OWNER = "owner";
const HISTORY_NAME = "Differential expression of liver samples, batch 2, trimmed and aligned to GRCh38";

function mountOwnHistoryCard() {
    const localVue = getLocalVue();
    useUserStore().setCurrentUser({ id: "user_id", email: "owner@example.org", username: OWNER } as RegisteredUser);
    // reactive like the entries of the history list
    const history = reactive({
        id: "history_id",
        name: HISTORY_NAME,
        username: OWNER,
        deleted: false,
        purged: false,
        tags: [],
        count: 3,
        update_time: "2026-01-01T00:00:00",
    }) as unknown as AnyHistoryEntry;
    const wrapper = mount(HistoryCard as object, {
        props: { history },
        global: {
            ...localVue,
            stubs: { ...localVue.stubs, FontAwesomeIcon: true, HistoryDatasetsBadge: true },
        },
    });
    return { wrapper, history };
}

/** Adds a tag the way the tag editor does: to the tags the card currently shows. */
async function addTag(wrapper: ReturnType<typeof mount>, tag: string) {
    const editor = wrapper.findComponent(StatelessTags);
    editor.vm.$emit("input", [...(editor.props("value") as string[]), tag]);
    await wrapper.vm.$nextTick();
}

describe("HistoryCard", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockedUpdateHistoryFields.mockReset();
    });

    it("shows the name of an owned history as plain text, not as a link", () => {
        const { wrapper } = mountOwnHistoryCard();

        expect(wrapper.find("#g-card-title-link-history-history_id").exists()).toBe(false);
        const title = wrapper.find("#g-card-title-text-history-history_id");
        expect(title.text()).toBe(HISTORY_NAME);
        expect(title.element.tagName).toBe("SPAN");
        expect(title.attributes("title")).toBe(HISTORY_NAME);
    });

    it("reloads the list when a tag save fails", async () => {
        mockedUpdateHistoryFields.mockRejectedValueOnce(new Error("save failed"));
        const { wrapper } = mountOwnHistoryCard();

        await addTag(wrapper, "first");
        await flushPromises();

        expect(Toast.error).toHaveBeenCalledTimes(1);
        expect(wrapper.emitted("refreshList")).toEqual([[true, true]]);
    });

    it("shows the saved tags again when a list reload during the save brought back older ones", async () => {
        const save = deferred();
        mockedUpdateHistoryFields.mockImplementationOnce(() => save.promise as never);
        const { wrapper, history } = mountOwnHistoryCard();

        await addTag(wrapper, "first");
        // the list was reloaded before the save reached the server
        const reloadedHistory = reactive({ ...history, tags: [] as string[] }) as unknown as AnyHistoryEntry;
        await wrapper.setProps({ history: reloadedHistory } as object);
        expect(wrapper.findComponent(StatelessTags).props("value")).toEqual([]);

        save.resolve({ id: "history_id", tags: ["first"] });
        await flushPromises();

        expect(mockedUpdateHistoryFields).toHaveBeenCalledWith("history_id", { tags: ["first"] });
        expect(reloadedHistory.tags).toEqual(["first"]);
        expect(wrapper.findComponent(StatelessTags).props("value")).toEqual(["first"]);
        expect(wrapper.emitted("refreshList")).toBeUndefined();
    });
});
