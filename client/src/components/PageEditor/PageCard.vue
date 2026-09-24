<script setup lang="ts">
import { faEdit, faEye, faHistory, faShareAlt, faSitemap, faUser } from "@fortawesome/free-solid-svg-icons";
import { computed } from "vue";

import type { HistoryPageSummary } from "@/api/pages";
import type { CardAction, CardBadge, Title } from "@/components/Common/GCard.types";
import { useUserStore } from "@/stores/userStore.js";

import GCard from "../Common/GCard.vue";

interface Props {
    page: HistoryPageSummary;
    defaultTitle?: string;
    entityName?: string;
    editTitle?: string;
    showInvocationBadge?: boolean;
    viewTitle?: string;
}

const props = withDefaults(defineProps<Props>(), {
    entityName: "Notebook",
    editTitle: "Edit Notebook",
    defaultTitle: "Untitled Notebook",
    viewTitle: "View Notebook",
});

const emit = defineEmits<{
    (e: "edit"): void;
    (e: "view"): void;
}>();

const userStore = useUserStore();

const title: Title = {
    label: props.page.title || props.defaultTitle,
    title: props.editTitle,
    handler: () => emit("edit"),
};

const badges = computed<CardBadge[]>(() => {
    const retBadges: CardBadge[] = [
        {
            id: "notebook-revisions-count",
            label: `${props.page.revision_ids.length} Revision${props.page.revision_ids.length !== 1 ? "s" : ""}`,
            icon: faHistory,
            title: "Number of revisions for this notebook",
            class: "unselectable",
        },
    ];
    if (!userStore.matchesCurrentUsername(props.page.username)) {
        retBadges.push({
            id: "owned-by-other-user",
            label: `Owned by ${props.page.username}`,
            icon: faUser,
            title: "This notebook is owned by another user. Editing it will create a copy owned by you.",
            class: "unselectable",
            variant: "outline-primary",
        });
    }
    if (props.showInvocationBadge && props.page.source_invocation_id) {
        retBadges.push({
            id: "is-invocation-notebook",
            label: `Invocation ${props.page.source_invocation_id}`,
            icon: faSitemap,
            title: "This notebook is a report created from a workflow invocation (Click to view the original report under the invocation)",
            class: "unselectable",
            to: `/workflows/invocations/${props.page.source_invocation_id}/reports?id=${props.page.id}`,
            variant: "info",
        });
    }
    return retBadges;
});

const primaryActions: CardAction[] = [
    {
        id: "edit-notebook",
        label: "Edit",
        icon: faEdit,
        title: !props.page.deleted ? props.editTitle : `This ${props.entityName} is deleted`,
        handler: () => emit("edit"),
        disabled: props.page.deleted,
    },
];

const secondaryActions: CardAction[] = [
    {
        id: "share-access-management",
        label: "Share and Publish",
        title: `Make this ${props.entityName} accessible or public`,
        icon: faShareAlt,
        variant: "outline-primary",
        to: `/pages/sharing?id=${props.page.id}`,
        visible: !props.page.deleted && userStore.matchesCurrentUsername(props.page.username),
    },
    {
        id: "view-notebook",
        label: "View",
        icon: faEye,
        title: props.viewTitle,
        handler: () => emit("view"),
    },
];
</script>

<template>
    <GCard
        :id="`page-${props.page.id}`"
        :badges="badges"
        :primary-actions="primaryActions"
        :published="props.page.published"
        :secondary-actions="secondaryActions"
        :title="title"
        title-size="text"
        :update-time="props.page.update_time" />
</template>
