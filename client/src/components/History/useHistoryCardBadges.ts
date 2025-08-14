import { faUser } from "@fortawesome/free-solid-svg-icons";
import { faCopy, faUsers } from "font-awesome-6";
import type { Ref } from "vue";

import type { AnyHistoryEntry, PublishedHistory, SharedHistory } from "@/api/histories";
import { currentUserOwnsHistory, isArchivedHistory, isPublishedHistory, isSharedHistory } from "@/api/histories";
import type { CardBadge } from "@/components/Common/GCard.types";
import localize from "@/utils/localization";

export function useHistoryCardBadges(
    history: Ref<AnyHistoryEntry>,
    sharedView: boolean,
    publishedView: boolean,
    updateFilter: (key: string, value: string) => void
) {
    function ownerBadgeTitle(h: SharedHistory | PublishedHistory): string {
        if (h.published && sharedView && !publishedView) {
            return localize(`Shared by '${h.username}'. Click to view all histories shared by '${h.username}'`);
        } else if (currentUserOwnsHistory(h.username)) {
            return localize("Published by you. Click to view all published histories by you");
        } else {
            return localize(`Published by '${h.username}'. Click to view all published histories by '${h.username}'`);
        }
    }

    const historyCardTitleBadges: CardBadge[] = [
        {
            id: "snapshot",
            label: localize("Snapshot available"),
            title: localize(
                "This history has an associated export record containing a snapshot of the history that can be used to import a copy of the history."
            ),
            icon: faCopy,
            visible: isArchivedHistory(history.value) && !!history.value.export_record_data,
        },
    ];

    if (isSharedHistory(history.value)) {
        const username = history.value.username;

        historyCardTitleBadges.unshift({
            id: "owner-shared",
            label: username,
            title: localize(
                `'${username}' shared this history with you. Click to view all histories shared with you by '${username}'`
            ),
            icon: faUsers,
            type: "badge",
            variant: "outline-secondary",
            handler: () => updateFilter("user", username),
            visible: !currentUserOwnsHistory(username) && sharedView,
        });
    }

    if (isPublishedHistory(history.value)) {
        const username = history.value.username;

        historyCardTitleBadges.unshift({
            id: "owner-published",
            label: username,
            title: ownerBadgeTitle(history.value),
            icon: faUser,
            type: "badge",
            variant: "outline-secondary",
            disabled: publishedView,
            handler: () => updateFilter("user", username),
            visible: publishedView,
        });
    }

    return { historyCardTitleBadges };
}
