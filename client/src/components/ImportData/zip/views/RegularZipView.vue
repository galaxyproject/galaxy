<script setup lang="ts">
import { computed } from "vue";

import { getImportableFiles, type IZipExplorer } from "@/composables/zipExplorer";

import GCard from "@/components/Common/GCard.vue";
import ZipFileEntrySummaryCard from "@/components/ImportData/zip/ZipFileEntrySummaryCard.vue";

const props = defineProps<{
    explorer: IZipExplorer;
}>();

const files = computed(() => getImportableFiles(props.explorer));

const zipFileBadges = [
    {
        id: "file-count",
        label: `${files.value.length} file${files.value.length > 1 ? "s" : ""} available`,
        title: "Number of Files available to import",
        visible: true,
    },
];
</script>

<template>
    <GCard
        id="regular-zip-summary-card"
        title="List of files contained in the ZIP archive"
        title-size="md"
        :badges="zipFileBadges">
        <template v-slot:description>
            <ZipFileEntrySummaryCard v-for="file in files" :key="file.path" :file="file" :selectable="false" />
        </template>
    </GCard>
</template>
