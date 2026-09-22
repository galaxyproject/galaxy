import type { HistoryItemSummary } from "@/api";
import { Toast } from "@/composables/toast";
import localize from "@/utils/localization";

/** `13: sample.fastq` - how every creator names a dataset in a notification. */
function describeElement(element: HistoryItemSummary): string {
    return `${element.hid}: ${element.name}`;
}

/**
 * Why a dataset cannot go into the collection being built. The creators show this both on
 * reconciliation and when an upload lands, under their own titles, so the sentence is shared
 * but the notification is not.
 */
export function invalidElementMessage(element: HistoryItemSummary, problem: string): string {
    return `${describeElement(element)} ${problem} and ${localize("is not a valid element for this collection")}`;
}

/**
 * Datasets the user had already committed to the collection under construction are gone from
 * the history. Several are described in one notification so that e.g. a vanished pair reads as
 * the single event it is.
 */
export function toastRemovedFromCollection(...elements: HistoryItemSummary[]) {
    const description = elements.map(describeElement).join(", ");
    Toast.error(`${description} ${localize("has been removed from the collection")}`, localize("Invalid element"));
}

/** A dataset is still in the history but can no longer go into this collection. */
function toastInvalidForCollection(element: HistoryItemSummary, problem: string) {
    Toast.error(invalidElementMessage(element, problem), localize("Invalid element"));
}

/**
 * A lesser-severity notice - a warning rather than an error - for datasets that disappeared but
 * were never actually headed into the final collection to begin with, so "removed from the
 * collection" would overstate what happened.
 */
export function toastNoLongerAvailable(element: HistoryItemSummary) {
    const msg = `${describeElement(element)} ${localize("is no longer available and was removed from the pairing list")}`;
    Toast.warning(msg, localize("Dataset unavailable"));
}

/**
 * The by-id seam the collection creators share: `initialElements` changed, so the candidates
 * are rebuilt from the prop and whatever the user had already chosen is projected back onto
 * them by id. A choice that no longer resolves - because the dataset left the history, or
 * because it is still there but no longer usable - is dropped and reported.
 *
 * `isElementInvalid` is the creator's own notion of usable; `useCollectionCreator` binds it.
 */
export function useElementReconciliation(isElementInvalid: (element: HistoryItemSummary) => string | null) {
    /** Project each retained choice onto `candidates`, in the order the user had them. */
    function reconcileRetainedElements<T extends HistoryItemSummary>(
        retained: readonly HistoryItemSummary[],
        candidates: readonly T[],
    ): T[] {
        const candidatesById = new Map(candidates.map((candidate) => [candidate.id, candidate]));
        const kept: T[] = [];

        for (const previous of retained) {
            const candidate = candidatesById.get(previous.id);
            if (!candidate) {
                toastRemovedFromCollection(previous);
                continue;
            }
            const problem = isElementInvalid(candidate);
            if (problem) {
                // describe the element as the user last saw it, not as the rebuilt pool renamed it
                toastInvalidForCollection(previous, problem);
                continue;
            }
            kept.push(candidate);
        }

        return kept;
    }

    /** As above for a creator holding single slots (a pair's forward/reverse) rather than a list. */
    function reconcileRetainedSlot<T extends HistoryItemSummary>(
        retained: HistoryItemSummary | undefined,
        candidates: readonly T[],
    ): T | undefined {
        if (!retained) {
            return undefined;
        }
        return reconcileRetainedElements([retained], candidates)[0];
    }

    return { reconcileRetainedElements, reconcileRetainedSlot };
}
