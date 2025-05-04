<script setup lang="ts">
import { faDatabase, faExclamationTriangle } from "@fortawesome/free-solid-svg-icons";
import { computed } from "vue";

import type { ImportableFile } from "@/composables/zipExplorer";
import localize from "@/utils/localization";
import { bytesToString } from "@/utils/utils";

import GCard from "@/components/Common/GCard.vue";

interface Props {
    file: ImportableFile;
    selectable?: boolean;
    selected?: boolean;
    gridView?: boolean;
    bytesLimit?: number;
}

const props = withDefaults(defineProps<Props>(), {
    selectable: true,
    selected: undefined,
    gridView: undefined,
    bytesLimit: undefined,
});

const emit = defineEmits<{
    (e: "select"): void;
}>();

const isSelectable = computed(() => {
    return props.selectable && !sizeLimitExceeded.value;
});

const sizeLimitExceeded = computed(() => {
    return props.bytesLimit ? props.file.size > props.bytesLimit : false;
});

const sizeLimitExceededMessage = computed(() => {
    return localize("File is too large to import due to browser limitations.");
});

const badges = [
    {
        id: "file-size",
        label: bytesToString(props.file.size, true, undefined),
        title: sizeLimitExceeded.value ? sizeLimitExceededMessage.value : "File size",
        icon: sizeLimitExceeded.value ? faExclamationTriangle : faDatabase,
        visible: true,
        variant: sizeLimitExceeded.value ? "danger" : undefined,
    },
];
</script>

<template>
    <GCard
        :id="file.path"
        :title="file.name"
        :badges="badges"
        :clickable="isSelectable"
        :selectable="isSelectable"
        :update-time="file.dateTime.toISOString()"
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
