<script setup lang="ts">
import { BPagination } from "bootstrap-vue";
import { computed } from "vue";

import type { CardBadge } from "@/components/Common/GCard.types";
import { usePagination } from "@/composables/pagination";
import { getImportableFiles, type IZipExplorer } from "@/composables/zipExplorer";

import GCard from "@/components/Common/GCard.vue";
import ZipFileEntrySummaryCard from "@/components/ImportData/zip/ZipFileEntrySummaryCard.vue";

const props = defineProps<{
    explorer: IZipExplorer;
}>();

const files = computed(() => getImportableFiles(props.explorer));

const {
    currentPage,
    itemsPerPage,
    paginatedItems: paginatedFiles,
    showPagination,
    onPageChange,
} = usePagination(files);

const zipFileBadges: CardBadge[] = [
    {
        id: "file-count",
        label: `${files.value.length} file${files.value.length > 1 ? "s" : ""} available`,
        title: "Number of Files available to import",
    },
];
</script>

<template>
    <div>
        <GCard
            id="regular-zip-summary-card"
            title="List of files contained in the archive"
            title-size="md"
            :badges="zipFileBadges">
            <template v-slot:description>
                <ZipFileEntrySummaryCard
                    v-for="file in paginatedFiles"
                    :key="file.path"
                    :file="file"
                    :selectable="false" />
            </template>
        </GCard>

        <div v-if="showPagination" class="regular-zip-footer mt-3">
            <BPagination
                :value="currentPage"
                :total-rows="files.length"
                :per-page="itemsPerPage"
                align="center"
                size="sm"
                first-number
                last-number
                @change="onPageChange" />
        </div>
    </div>
</template>

<style scoped lang="scss">
.regular-zip-footer {
    display: flex;
    justify-content: center;
    padding: 1rem 0;
    border-top: 1px solid #dee2e6;
}
</style>
