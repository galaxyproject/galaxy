<script setup lang="ts">
import { faArchive, faDatabase, faInfoCircle, faTrash, faUndo } from "@fortawesome/free-solid-svg-icons";
import { computed } from "vue";

import { useHistoryStore } from "@/stores/historyStore";
import { bytesToString } from "@/utils/utils";

import type { DataValuePoint } from "./Charts";

import GCard from "@/components/Common/GCard.vue";

type ItemTypes = "history" | "dataset";

interface SelectedItemActionsProps {
    data: DataValuePoint;
    isRecoverable: boolean;
    itemType: ItemTypes;
    isArchived?: boolean;
    canEdit?: boolean;
}

const { currentHistoryId, setCurrentHistory } = useHistoryStore();

const props = withDefaults(defineProps<SelectedItemActionsProps>(), {
    isArchived: false,
    canEdit: false,
});

const label = computed(() => props.data?.label ?? "No data");
const prettySize = computed(() => bytesToString(props.data?.value ?? 0));
const canSetAsCurrent = computed(() => props.itemType === "history" && props.data.id !== currentHistoryId);

const emit = defineEmits<{
    (e: "set-current-history", historyId: string): void;
    (e: "view-item", itemId: string): void;
    (e: "undelete-item", itemId: string): void;
    (e: "permanently-delete-item", itemId: string): void;
}>();

function onUndeleteItem() {
    emit("undelete-item", props.data.id);
}

async function onSetCurrentHistory() {
    await setCurrentHistory(props.data.id);
}

function onViewItem() {
    emit("view-item", props.data.id);
}

function onPermanentlyDeleteItem() {
    emit("permanently-delete-item", props.data.id);
}

const titleIcon = computed(() => {
    return props.isArchived
        ? { icon: faArchive, title: "This item is archived" }
        : { icon: faInfoCircle, title: `Details of this ${props.itemType}` };
});

const badges = computed(() => [
    {
        id: "count",
        label: prettySize.value,
        title: "Total storage space taken",
        icon: faDatabase,
        visible: true,
    },
]);

const description = computed(() => {
    let ds = "";

    if (props.isArchived) {
        ds = `This ${props.itemType} is archived.`;
    }
    if (props.isRecoverable) {
        ds = `This ${props.itemType} was deleted. You can **undelete** it or **permanently delete** it to free up its storage space.`;
    }

    return ds;
});

const primaryActions = computed(() => {
    return [
        {
            id: "undelete",
            label: "Restore",
            icon: faUndo,
            title: `Undelete this ${props.itemType}`,
            variant: "outline-primary",
            handler: onUndeleteItem,
            visible: props.isRecoverable && props.canEdit,
        },
        {
            id: "delete",
            label: "Delete",
            icon: faTrash,
            title: `Permanently delete this ${props.itemType}`,
            variant: "outline-danger",
            handler: onPermanentlyDeleteItem,
            visible: props.canEdit,
        },
        {
            id: "select",
            label: "Set as current",
            title: "Set this history as current",
            variant: "outline-primary",
            handler: onSetCurrentHistory,
            visible: canSetAsCurrent.value,
        },
        {
            id: "explore",
            label: "Explore content",
            icon: faInfoCircle,
            title: `Explore the content of this ${props.itemType}`,
            variant: "outline-primary",
            handler: onViewItem,
            visible: true,
        },
    ];
});
</script>

<template>
    <GCard
        :id="`selected-item-actions-${props.itemType}`"
        :title="label"
        :title-icon="titleIcon"
        :badges="badges"
        full-description
        :description="description"
        :primary-actions="primaryActions" />
</template>
