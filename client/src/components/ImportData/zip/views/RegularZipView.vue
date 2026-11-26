<script setup lang="ts">
import { computed } from "vue";

import type { CardBadge } from "@/components/Common/GCard.types";
import { usePagination } from "@/composables/pagination";
import { getImportableFiles, type IZipExplorer } from "@/composables/zipExplorer";

import GPagination from "@/components/BaseComponents/GPagination.vue";
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

        <div v-if="showPagination" class="d-flex justify-content-center py-3 mt-3">
            <GPagination
                :model-value="currentPage"
                :total-rows="files.length"
                :per-page="itemsPerPage"
                align="center"
                size="small"
                first-number
                last-number
                @change="onPageChange" />
        </div>
    </div>
</template>
