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
    it("offers the export on the user's own history", () => {
        expect(offersExport({})()).toBe(true);
        expect(offersExport({}, false)()).toBe(false);
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

    it("offers no export on someone else's history, even where the item is marked writable", () => {
        expect(offersExport({ history_id: "theirs" })()).toBe(false);
    });

    it("offers no export on an archived history, as the history panel does not", () => {
        expect(offersExport({ history_id: "archived" })()).toBe(false);
    });

    it("offers no export for a deleted dataset, which the other Galaxy would import out of sight", () => {
        expect(offersExport({ deleted: true })()).toBe(false);
    });
});
