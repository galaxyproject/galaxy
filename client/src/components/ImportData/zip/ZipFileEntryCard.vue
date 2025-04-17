<script setup lang="ts">
import { faDatabase } from "@fortawesome/free-solid-svg-icons";

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
        :badges="badges"
        clickable
        :update-time="file.dateTime.toISOString()"
        selectable
        :grid-view="props.gridView"
        :selected="props.selected"
        @select="emit('select')"
        @click="emit('select')">
        <template v-slot:description>
            <div v-if="file.path !== file.name" class="zip-file-path text-muted">
                {{ file.path }}
            </div>

            <div v-if="file.description">
                {{ file.description }}
            </div>
        </template>
    </GCard>
</template>

<style scoped lang="scss">
.zip-file-path {
    font-size: 0.9rem;
    font-style: italic;
    margin-bottom: 0.5rem;
    word-break: break-all;
    overflow-wrap: break-word;
}
</style>
