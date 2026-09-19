import { faBurn, faGlobe, faTrash } from "@fortawesome/free-solid-svg-icons";
import { storeToRefs } from "pinia";
import type { Ref } from "vue";

import { userOwnsHistory } from "@/api";
import type { AnyHistoryEntry, PublishedHistory } from "@/api/histories";
import { isPublishedHistory } from "@/api/histories";
import type { CardIndicator } from "@/components/Common/GCard.types";
import { useUserStore } from "@/stores/userStore";
import localize from "@/utils/localization";

/**
 * Custom composable for managing history card visual indicators
 *
 * Provides visual indicator configurations for history cards including
 * status indicators for different history states (deleted, purged, published).
 * Indicators serve as visual cues and may include click handlers for filtering.
 *
 * @param {Ref<AnyHistoryEntry>} history - Reactive reference to the history entry
 * @param {boolean} publishedView - Whether the card is displayed in published histories view
 * @param {(key: string, value: boolean) => void} updateFilter - Callback to update filter values
 * @returns {Object} Object containing the historyCardIndicators array
 *
 * @example
 * const { historyCardIndicators } = useHistoryCardIndicators(
 *   historyRef,
 *   false,
 *   (key, value) => updateFilter(key, value)
 * );
 */
export function useHistoryCardIndicators(
    history: Ref<AnyHistoryEntry>,
    publishedView: boolean,
    updateFilter: (key: string, value: boolean) => void,
): {
    historyCardIndicators: CardIndicator[];
} {
    /**
     * Generates appropriate tooltip text for published history indicators
     *
     * @param {PublishedHistory} h - The published history
     * @returns {string} Localized tooltip text for the published indicator
     */
    function publishedIndicatorTitle(h: PublishedHistory): string {
        const { currentUser } = storeToRefs(useUserStore());

        if (h.published && !publishedView) {
            return localize("Published history. Click to filter published histories");
        } else if (userOwnsHistory(currentUser.value, h)) {
            return localize("Published by you");
        } else {
            return localize(`Published by '${h.username}'`);
        }
    }

    /**
     * Array of visual indicators for history cards
     * Contains status indicators for deleted, purged, and published states
     * @type {CardIndicator[]}
     */
    const historyCardIndicators: CardIndicator[] = [
        {
            id: "deleted",
            label: "",
            title: localize("This history has been deleted."),
            icon: faTrash,
            disabled: publishedView,
            visible: history.value.deleted && !history.value.purged,
        },
        {
            id: "purged",
            label: "",
            title: localize("This history has been permanently deleted"),
            icon: faBurn,
            variant: "danger",
            disabled: publishedView,
            visible: history.value.purged,
        },
    ];

    /*
     * Adds published indicator for published histories
     */
    if (isPublishedHistory(history.value)) {
        historyCardIndicators.push({
            id: "published",
            label: "",
            title: publishedIndicatorTitle(history.value),
            icon: faGlobe,
            handler: () => updateFilter("published", true),
            disabled: publishedView,
            visible: true,
        });
    }

    return {
        historyCardIndicators,
    };
}
