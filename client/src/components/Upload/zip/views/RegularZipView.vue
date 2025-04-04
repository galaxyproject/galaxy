<script setup lang="ts">
import { computed } from "vue";

import { getImportableFiles, type IZipExplorer } from "@/composables/zipExplorer";

import Heading from "@/components/Common/Heading.vue";
import ZipFileEntryCard from "@/components/ImportData/zip/ZipFileEntryCard.vue";

const props = defineProps<{
    explorer: IZipExplorer;
}>();

const files = computed(() => getImportableFiles(props.explorer));
</script>

<template>
    <div class="rocrate-explorer">
        <Heading size="lg">ZIP Contents Summary</Heading>

        <Heading size="md">Files</Heading>
        <ZipFileEntryCard v-for="file in files" :key="file.path" :file="file" />
    </div>
</template>
