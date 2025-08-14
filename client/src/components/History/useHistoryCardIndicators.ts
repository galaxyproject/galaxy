import { faBurn, faGlobe, faTrash } from "@fortawesome/free-solid-svg-icons";
import { storeToRefs } from "pinia";
import type { Ref } from "vue";

import { userOwnsHistory } from "@/api";
import type { AnyHistoryEntry, PublishedHistory } from "@/api/histories";
import { isPublishedHistory } from "@/api/histories";
import type { CardIndicator } from "@/components/Common/GCard.types";
import { useUserStore } from "@/stores/userStore";
import localize from "@/utils/localization";

export function useHistoryCardIndicators(
    history: Ref<AnyHistoryEntry>,
    publishedView: boolean,
    updateFilter: (key: string, value: boolean) => void
) {
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
