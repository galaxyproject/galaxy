import { faStar as farStar } from "@fortawesome/free-regular-svg-icons";
import { faExternalLinkAlt, faLink, faStar as fasStar, faWrench } from "@fortawesome/free-solid-svg-icons";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import { getFullAppUrl } from "@/app/utils";
import type { CardAction } from "@/components/Common/GCard.types";
import { useGlobalUploadModal } from "@/composables/globalUploadModal";
import { useToast } from "@/composables/toast";
import { useUserStore } from "@/stores/userStore";
import ariaAlert from "@/utils/ariaAlert";
import { copy } from "@/utils/clipboard";

export function useToolsListCardActions(
    toolId: string,
    local?: boolean, // Maybe this shouldn't be conditional?
    name?: string,
    formStyle?: string,
    version?: string,
    to?: string,
    href?: string,
) {
    const userStore = useUserStore();
    const { currentFavorites, isAnonymous } = storeToRefs(userStore);

    const Toast = useToast();

    const { openGlobalUploadModal } = useGlobalUploadModal();

    const canBeRun = computed(() => formStyle === "regular" || !local);

    // Tool Favorite refs
    const isFavorite = computed(() => currentFavorites.value.tools?.includes(toolId));
    const favoriteButtonIcon = computed(() => (isAnonymous.value || !isFavorite.value ? farStar : fasStar));
    const favoriteButtonLabel = computed(() => {
        if (isAnonymous.value || !isFavorite.value) {
            return "Favorite Tool";
        }
        return "Unfavorite";
    });
    const favoriteButtonTitle = computed(() => {
        if (isAnonymous.value) {
            return "Login or Register to Favorite Tools";
        }
        if (isFavorite.value) {
            return "Remove from Favorites";
        }
        return "Add to Favorites";
    });
    const isTogglingFavorite = ref(false);

    // Tool Favorite Methods
    async function onAddFavorite() {
        try {
            isTogglingFavorite.value = true;
            await userStore.addFavoriteTool(toolId);
            ariaAlert("added to favorites");
        } catch {
            Toast.error(`Failed to add '${toolId}' to favorites.`);
            ariaAlert("failed to add to favorites");
        } finally {
            isTogglingFavorite.value = false;
        }
    }
    async function onRemoveFavorite() {
        try {
            isTogglingFavorite.value = true;
            await userStore.removeFavoriteTool(toolId);
            ariaAlert("removed from favorites");
        } catch {
            Toast.error(`Failed to remove '${toolId}' from favorites.`);
            ariaAlert("failed to remove from favorites");
        } finally {
            isTogglingFavorite.value = false;
        }
    }
    async function onToggleFavorite() {
        if (isAnonymous.value) {
            Toast.error("You must be signed in to manage favorites.");
            ariaAlert("sign in to manage favorites");
            return;
        }

        if (isFavorite.value) {
            await onRemoveFavorite();
        } else {
            await onAddFavorite();
        }
    }

    /** For the upload tool, we have no `to` or `href`, and we open the modal instead */
    function openUploadIfNeeded() {
        if (toolId === "upload1") {
            openGlobalUploadModal();
        }
    }

    const favoriteToolAction = computed(
        (): CardAction => ({
            id: "favorite-tool",
            label: favoriteButtonLabel.value,
            icon: favoriteButtonIcon.value,
            title: favoriteButtonTitle.value,
            disabled: isAnonymous.value || isTogglingFavorite.value,
            variant: "outline-primary", // TODO: Make this change conditionally
            handler: onToggleFavorite,
        }),
    );

    const toolsListCardSecondaryActions = computed((): CardAction[] => [
        {
            id: "copy-tool-link",
            label: "Copy Link",
            icon: faLink,
            title: "Copy Link to Tool",
            handler: () => {
                const copyableLink = href
                    ? getFullAppUrl(href.substring(1))
                    : getFullAppUrl(`?tool_id=${encodeURIComponent(toolId)}${version ? `&version=${version}` : ""}`);
                copy(copyableLink);
                Toast.success(`Link to ${name || "tool"} copied to clipboard`);
            },
            visible: canBeRun.value && toolId !== "upload1",
        },
        favoriteToolAction.value,
    ]);

    const toolsListCardPrimaryActions = computed((): CardAction[] => [
        {
            id: "open-tool",
            label: "Open",
            icon: local ? faWrench : faExternalLinkAlt,
            title: local ? "Open tool in Galaxy" : "Open tool in external site",
            visible: canBeRun.value,
            to: to,
            href: href,
            handler: openUploadIfNeeded,
        },
    ]);

    return {
        toolsListCardSecondaryActions,
        toolsListCardPrimaryActions,
        openUploadIfNeeded,
        favoriteToolAction,
    };
}
