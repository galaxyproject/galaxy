<script setup lang="ts">
import { faFileExport } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import { useConfig } from "@/composables/config";
import { useExportToAnotherGalaxyStore } from "@/stores/exportToAnotherGalaxyStore";

import GButton from "@/components/BaseComponents/GButton.vue";

const props = withDefaults(
    defineProps<{
        historyId: string;
        contentId: string;
        contentName: string;
        contentType?: "dataset" | "dataset_collection";
        /** Shown next to the icon, as on the collection buttons; without it the button is icon-only. */
        label?: string;
    }>(),
    { contentType: "dataset", label: undefined },
);

const { config } = useConfig(true);
const store = useExportToAnotherGalaxyStore();

function onExport() {
    store.open({
        historyId: props.historyId,
        contentType: props.contentType,
        contentId: props.contentId,
        contentName: props.contentName,
    });
}
</script>

<template>
    <GButton
        v-if="config?.enable_celery_tasks"
        v-g-tooltip.hover
        :class="{ 'px-1': !props.label }"
        title="Export to another Galaxy"
        size="small"
        :color="props.label ? 'blue' : undefined"
        transparent
        data-description="export to another galaxy"
        @click.stop="onExport">
        <FontAwesomeIcon :fixed-width="Boolean(props.label)" :icon="faFileExport" />
        <span v-if="props.label">{{ props.label }}</span>
    </GButton>
</template>
