import { createTestingPinia } from "@pinia/testing";
import { setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { AnyHistory } from "@/api";
import { useHistoryStore } from "@/stores/historyStore";

import { useCollectionCreation } from "./useCollectionCreation";

beforeEach(() => {
    setActivePinia(createTestingPinia({ createSpy: vi.fn }));
    // the only stored history is the current one
    useHistoryStore().storedHistories = { "history-1": { id: "history-1", name: "current" } as AnyHistory };
});

describe("useCollectionCreation", () => {
    it("falls back to the current history", () => {
        const { createPayload } = useCollectionCreation();
        expect(createPayload("reads", "list", [], false).history_id).toBe("history-1");
    });
});
