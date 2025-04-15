<script setup lang="ts">
import { faDatabase, faFile } from "@fortawesome/free-solid-svg-icons";

import type { CardBadge } from "@/components/Common/GCard.types";
import type { ImportableFile } from "@/composables/zipExplorer";
import { bytesToString } from "@/utils/utils";

import GCard from "@/components/Common/GCard.vue";

interface Props {
    file: ImportableFile;
    gridView?: boolean;
    selected?: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "select"): void;
}>();

const titleBadges: CardBadge[] = [
    {
        id: "file-path",
        label: props.file.path,
        title: "File Path",
        icon: faFile,
        type: "badge",
        variant: "secondary",
        visible: true,
    },
];

const badges = [
    {
        id: "file-size",
        label: bytesToString(props.file.size, true, undefined),
        title: "File Size",
        icon: faDatabase,
        visible: true,
    },
];
</script>

<template>
    <GCard
        :id="file.path"
        :title="file.name"
        :title-badges="titleBadges"
        :badges="badges"
        :description="file.description"
        clickable
        :update-time="file.dateTime.toISOString()"
        selectable
        :grid-view="props.gridView"
        :selected="props.selected"
        @select="emit('select')"
        @click="emit('select')">
    </GCard>
</template>
