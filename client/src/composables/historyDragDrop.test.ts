import { createTestingPinia } from "@pinia/testing";
import { setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import { useEventStore } from "@/stores/eventStore";
import { useHistoryStore } from "@/stores/historyStore";

import { useHistoryDragDrop } from "./historyDragDrop";

vi.mock("@/composables/toast");

const { server, http } = useServerMock();

const SOURCE_HISTORY_ID = "source-history";
const TARGET_HISTORY_ID = "target-history";
const NEW_HISTORY_ID = "new-history";

const DATASET = { id: "dataset-1", history_id: SOURCE_HISTORY_ID, history_content_type: "dataset" };
const COLLECTION = { id: "collection-1", history_id: SOURCE_HISTORY_ID, history_content_type: "dataset_collection" };

interface CopyRequest {
    historyId: string;
    content: unknown;
    source: unknown;
}

let copyRequests: CopyRequest[];

function setUp(dragItems: object[]) {
    setActivePinia(createTestingPinia({ createSpy: vi.fn }));
    const eventStore = useEventStore();
    vi.mocked(eventStore.getDragItems).mockReturnValue(dragItems as ReturnType<typeof eventStore.getDragItems>);
    return useHistoryStore();
}

function setUpNewHistoryBoxDrop(dragItems: object[]) {
    const historyStore = setUp(dragItems);
    historyStore.pinnedHistories = [{ id: SOURCE_HISTORY_ID }];
    vi.mocked(historyStore.createNewHistory).mockImplementation(async () => {
        // @ts-expect-error -- createTestingPinia makes getters writable
        historyStore.currentHistoryId = NEW_HISTORY_ID;
    });
    return historyStore;
}

describe("useHistoryDragDrop", () => {
    beforeEach(() => {
        copyRequests = [];
        server.use(
            http.post("/api/histories/{history_id}/contents/{type}s", async ({ params, request, response }) => {
                const body = (await request.json()) as { content: unknown; source: unknown };
                copyRequests.push({ historyId: params.history_id, content: body.content, source: body.source });
                return response(200).json({ id: body.content } as never);
            }),
        );
    });

    it("refreshes the target history after copying datasets and collections", async () => {
        const historyStore = setUp([DATASET, COLLECTION]);
        await useHistoryDragDrop(TARGET_HISTORY_ID).onDrop();
        expect(copyRequests).toEqual([
            { historyId: TARGET_HISTORY_ID, content: DATASET.id, source: "hda" },
            { historyId: TARGET_HISTORY_ID, content: COLLECTION.id, source: "hdca" },
        ]);
        expect(historyStore.loadHistoryById).toHaveBeenCalledWith(TARGET_HISTORY_ID);
        expect(historyStore.pinHistory).not.toHaveBeenCalled();
    });

    it("pins the new and source histories after dropping on the new history box", async () => {
        const historyStore = setUpNewHistoryBoxDrop([DATASET, COLLECTION]);
        await useHistoryDragDrop(undefined, true, true).onDrop();
        expect(historyStore.createNewHistory).toHaveBeenCalled();
        expect(copyRequests.map(({ historyId }) => historyId)).toEqual([NEW_HISTORY_ID, NEW_HISTORY_ID]);
        expect(historyStore.pinHistory).toHaveBeenCalledWith(NEW_HISTORY_ID);
        expect(historyStore.pinHistory).toHaveBeenCalledWith(SOURCE_HISTORY_ID);
        expect(historyStore.loadHistoryById).not.toHaveBeenCalled();
    });

    it("does not refresh the target history when the copy fails", async () => {
        server.use(
            http.post("/api/histories/{history_id}/contents/{type}s", ({ response }) =>
                response("5XX").json({ err_code: 500, err_msg: "Copy failed" }, { status: 500 }),
            ),
        );
        const historyStore = setUp([DATASET]);
        await useHistoryDragDrop(TARGET_HISTORY_ID).onDrop();
        expect(historyStore.loadHistoryById).not.toHaveBeenCalled();
        expect(historyStore.pinHistory).not.toHaveBeenCalled();
    });

    it("does not copy into the history the items came from", async () => {
        const historyStore = setUp([DATASET]);
        await useHistoryDragDrop(SOURCE_HISTORY_ID).onDrop();
        expect(copyRequests).toEqual([]);
        expect(historyStore.loadHistoryById).not.toHaveBeenCalled();
    });
});
