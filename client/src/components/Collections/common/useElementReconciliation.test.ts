import { beforeEach, describe, expect, it, vi } from "vitest";

import type { HDASummary, HistoryItemSummary } from "@/api";
import { Toast } from "@/composables/toast";

import {
    invalidElementMessage,
    toastNoLongerAvailable,
    toastRemovedFromCollection,
    useElementReconciliation,
} from "./useElementReconciliation";

vi.mock("@/composables/toast");

const toastError = vi.mocked(Toast.error);
const toastWarning = vi.mocked(Toast.warning);

beforeEach(() => {
    vi.clearAllMocks();
});

function fakeDataset(id: string, hid: number, name: string): HDASummary {
    return { id, hid, name, history_content_type: "dataset" } as unknown as HDASummary;
}

/** Nothing is ever invalid - the default for tests about presence, not validity. */
const allValid = () => null;

describe("useElementReconciliation", () => {
    describe("reconcileRetainedElements", () => {
        it("projects retained choices onto the rebuilt candidates by id", () => {
            const { reconcileRetainedElements } = useElementReconciliation(allValid);
            const retained = [fakeDataset("a", 1, "one"), fakeDataset("b", 2, "two")];
            // different objects, different order, renamed - exactly what _elementsSetUp produces
            const rebuilt = [fakeDataset("b", 2, "two (1)"), fakeDataset("a", 1, "one")];

            const kept = reconcileRetainedElements(retained, rebuilt);

            expect(kept.map((element) => element.id)).toEqual(["a", "b"]);
            expect(kept[1]).toBe(rebuilt[0]);
            expect(toastError).not.toHaveBeenCalled();
        });

        it("drops a retained element that is gone and says it was removed from the collection", () => {
            const { reconcileRetainedElements } = useElementReconciliation(allValid);
            const gone = fakeDataset("b", 2, "two");

            const kept = reconcileRetainedElements([fakeDataset("a", 1, "one"), gone], [fakeDataset("a", 1, "one")]);

            expect(kept.map((element) => element.id)).toEqual(["a"]);
            expect(toastError).toHaveBeenCalledTimes(1);
            expect(toastError).toHaveBeenCalledWith("2: two has been removed from the collection", "Invalid element");
        });

        it("drops a retained element that has become invalid and says why", () => {
            const { reconcileRetainedElements } = useElementReconciliation((element: HistoryItemSummary) =>
                element.id === "b" ? "has errored, is paused, or is not accessible" : null,
            );

            const kept = reconcileRetainedElements(
                [fakeDataset("a", 1, "one"), fakeDataset("b", 2, "two")],
                [fakeDataset("a", 1, "one"), fakeDataset("b", 2, "two")],
            );

            expect(kept.map((element) => element.id)).toEqual(["a"]);
            expect(toastError).toHaveBeenCalledWith(
                "2: two has errored, is paused, or is not accessible and is not a valid element for this collection",
                "Invalid element",
            );
        });

        it("describes an invalid element as the user last saw it, not as the rebuilt pool renamed it", () => {
            const { reconcileRetainedElements } = useElementReconciliation(() => "has been deleted or purged");

            reconcileRetainedElements([fakeDataset("a", 7, "sample.fastq")], [fakeDataset("a", 7, "sample")]);

            expect(toastError).toHaveBeenCalledWith(
                "7: sample.fastq has been deleted or purged and is not a valid element for this collection",
                "Invalid element",
            );
        });

        it("keeps nothing and says nothing when nothing was retained", () => {
            const { reconcileRetainedElements } = useElementReconciliation(allValid);

            expect(reconcileRetainedElements([], [fakeDataset("a", 1, "one")])).toEqual([]);
            expect(toastError).not.toHaveBeenCalled();
        });
    });

    describe("reconcileRetainedSlot", () => {
        it("projects a single retained choice onto the rebuilt candidates", () => {
            const { reconcileRetainedSlot } = useElementReconciliation(allValid);
            const rebuilt = [fakeDataset("a", 1, "one")];

            expect(reconcileRetainedSlot(fakeDataset("a", 1, "one"), rebuilt)).toBe(rebuilt[0]);
        });

        it("returns undefined for an empty slot without notifying anyone", () => {
            const { reconcileRetainedSlot } = useElementReconciliation(allValid);

            expect(reconcileRetainedSlot(undefined, [fakeDataset("a", 1, "one")])).toBeUndefined();
            expect(toastError).not.toHaveBeenCalled();
        });

        it("returns undefined and notifies when the retained choice is gone", () => {
            const { reconcileRetainedSlot } = useElementReconciliation(allValid);

            expect(reconcileRetainedSlot(fakeDataset("b", 2, "two"), [])).toBeUndefined();
            expect(toastError).toHaveBeenCalledWith("2: two has been removed from the collection", "Invalid element");
        });
    });

    describe("notifications", () => {
        it("says why an element cannot go into the collection, for reconciliation and uploads alike", () => {
            expect(invalidElementMessage(fakeDataset("a", 3, "one"), "has been deleted or purged")).toBe(
                "3: one has been deleted or purged and is not a valid element for this collection",
            );
        });

        it("describes a vanished pair in a single message rather than one per side", () => {
            toastRemovedFromCollection(fakeDataset("a", 1, "one"), fakeDataset("b", 2, "two"));

            expect(toastError).toHaveBeenCalledTimes(1);
            expect(toastError).toHaveBeenCalledWith(
                "1: one, 2: two has been removed from the collection",
                "Invalid element",
            );
        });

        it("warns rather than errors for an element that was never headed into the collection", () => {
            toastNoLongerAvailable(fakeDataset("a", 1, "one"));

            expect(toastError).not.toHaveBeenCalled();
            expect(toastWarning).toHaveBeenCalledWith(
                "1: one is no longer available and was removed from the pairing list",
                "Dataset unavailable",
            );
        });
    });
});
