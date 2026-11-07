<script setup lang="ts">
import { computed } from "vue";

import { usePagination } from "@/composables/pagination";
import { type GalaxyZipExplorer, getImportableFiles } from "@/composables/zipExplorer";

import GPagination from "@/components/BaseComponents/GPagination.vue";
import Heading from "@/components/Common/Heading.vue";
import ZipFileEntryCard from "@/components/ImportData/zip/ZipFileEntryCard.vue";

const props = defineProps<{
    explorer: GalaxyZipExplorer;
}>();

const files = computed(() => getImportableFiles(props.explorer));

const {
    currentPage,
    itemsPerPage,
    paginatedItems: paginatedFiles,
    showPagination,
    onPageChange,
} = usePagination(files);
</script>

<template>
    <div class="galaxy-zip-explorer">
        <Heading size="lg">Galaxy Export Archive Summary</Heading>
        <Heading size="md">Files</Heading>

        <ZipFileEntryCard v-for="file in paginatedFiles" :key="file.path" :file="file" />

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
