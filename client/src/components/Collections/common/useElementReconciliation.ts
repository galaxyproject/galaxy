import type { HistoryItemSummary } from "@/api";
import { Toast } from "@/composables/toast";
import localize from "@/utils/localization";

/** `13: sample.fastq` - how every creator names a dataset in a notification. */
function describeElement(element: HistoryItemSummary): string {
    return `${element.hid}: ${element.name}`;
}

/** Shared wording - each creator raises it under its own title, on reconciliation and on upload. */
export function invalidElementMessage(element: HistoryItemSummary, problem: string): string {
    return `${describeElement(element)} ${problem} and ${localize("is not a valid element for this collection")}`;
}

/** Several elements per notification, so e.g. a vanished pair reads as one event. */
export function toastRemovedFromCollection(...elements: HistoryItemSummary[]) {
    const description = elements.map(describeElement).join(", ");
    Toast.error(`${description} ${localize("has been removed from the collection")}`, localize("Invalid element"));
}

function toastInvalidForCollection(element: HistoryItemSummary, problem: string) {
    Toast.error(invalidElementMessage(element, problem), localize("Invalid element"));
}

/** Warning rather than error: these were never headed into the final collection. */
export function toastNoLongerAvailable(element: HistoryItemSummary) {
    const msg = `${describeElement(element)} ${localize("is no longer available and was removed from the pairing list")}`;
    Toast.warning(msg, localize("Dataset unavailable"));
}

/**
 * `initialElements` changed: candidates are rebuilt from the prop and the user's existing choices
 * are projected back onto them by id. A choice that no longer resolves - gone from the history, or
 * still there but no longer usable - is dropped and reported.
 */
export function useElementReconciliation(isElementInvalid: (element: HistoryItemSummary) => string | null) {
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
                // report it as the user last saw it, not as the rebuilt pool renamed it
                toastInvalidForCollection(previous, problem);
                continue;
            }
            kept.push(candidate);
        }

        return kept;
    }

    /** As above, for a single slot (a pair's forward/reverse) rather than a list. */
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
