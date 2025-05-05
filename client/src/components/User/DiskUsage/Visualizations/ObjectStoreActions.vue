<script setup lang="ts">
import { faInfoCircle } from "@fortawesome/free-solid-svg-icons";

import type { DataValuePoint } from "./Charts";

import GCard from "@/components/Common/GCard.vue";

interface Props {
    data: DataValuePoint;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "view-item", itemId: string): void;
}>();

function onViewItem() {
    emit("view-item", props.data.id);
}

const primaryActions = [
    {
        id: "view",
        label: "View",
        icon: faInfoCircle,
        title: "Go to the details of this storage location",
        variant: "outline-primary",
        handler: onViewItem,
        visible: true,
    },
];
</script>

<template>
    <GCard :id="props.data.id" :title="props.data.label" :primary-actions="primaryActions" />
</template>
