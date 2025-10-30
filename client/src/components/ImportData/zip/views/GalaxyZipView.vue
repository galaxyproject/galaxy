<script setup lang="ts">
import { BPagination } from "bootstrap-vue";
import { computed } from "vue";

import { usePagination } from "@/composables/pagination";
import { type GalaxyZipExplorer, getImportableFiles } from "@/composables/zipExplorer";

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

        <div v-if="showPagination" class="galaxy-zip-footer mt-3">
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
@import "theme/blue.scss";

.galaxy-zip-footer {
    display: flex;
    justify-content: center;
    padding: 1rem 0;
    border-top: 1px solid $brand-secondary;
}
</style>
