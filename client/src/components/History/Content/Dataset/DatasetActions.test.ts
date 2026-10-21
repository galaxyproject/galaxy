import { createTestingPinia } from "@pinia/testing";
import { getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import DatasetActions from "./DatasetActions.vue";
import ExportToAnotherGalaxy from "@/components/History/Content/ExportToAnotherGalaxy.vue";

const { server, http } = useServerMock();

function offersExport(item: Record<string, unknown>, writable = true) {
    const pinia = createTestingPinia({
        createSpy: vi.fn,
        stubActions: false,
        initialState: {
            userStore: { currentUser: getFakeRegisteredUser({ id: "u1" }) },
            historyStore: {
                storedHistories: {
                    mine: { id: "mine", name: "Mine", user_id: "u1" },
                    theirs: { id: "theirs", name: "Theirs", user_id: "u2" },
                    archived: { id: "archived", name: "Archived", user_id: "u1", archived: true },
                },
            },
        },
    });
    const wrapper = shallowMount(DatasetActions as object, {
        global: withPlugins(getLocalVue(), pinia),
        props: {
            item: {
                id: "d1",
                history_id: "mine",
                name: "reads.bed",
                purged: false,
                deleted: false,
                visible: true,
                state: "ok",
                ...item,
            },
            itemUrls: { edit: "", showDetails: null },
            writable,
            showHighlight: false,
        },
    });
    return () => wrapper.findComponent(ExportToAnotherGalaxy).exists();
}

describe("DatasetActions", () => {
    it.each([
        ["a finished dataset in the user's own history", true, {}, true],
        ["an item that is not writable here", false, {}, false],
        ["someone else's history, even where the item is marked writable", false, { history_id: "theirs" }, true],
        ["an archived history", false, { history_id: "archived" }, true],
        ["a deleted dataset", false, { deleted: true }, true],
        ["a hidden dataset", false, { visible: false }, true],
        ["a dataset that is still running", false, { state: "running" }, true],
    ])("for %s, offers the export: %s", (_, offered, item, writable) => {
        expect(offersExport(item, writable)()).toBe(offered);
    });

    it("offers the export on an own history that was not loaded yet", async () => {
        server.use(
            http.get("/api/histories/{history_id}", ({ response }) =>
                response(200).json({ id: "older", name: "Older", user_id: "u1" } as never),
            ),
        );
        const offered = offersExport({ history_id: "older" });
        expect(offered()).toBe(false);
        await flushPromises();
        expect(offered()).toBe(true);
    });
});
