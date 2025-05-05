<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import type { ArchiveSource, ImportableFile, ImportableZipContents } from "@/composables/zipExplorer";
import { useUserStore } from "@/stores/userStore";

import Heading from "@/components/Common/Heading.vue";
import ListHeader from "@/components/Common/ListHeader.vue";
import ZipFileEntryCard from "@/components/ImportData/zip/ZipFileEntryCard.vue";

interface Props {
    zipSource: ArchiveSource;
    zipContents: ImportableZipContents;
    selectedItems: ImportableFile[];
    bytesLimit?: number;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "update:selectedItems", value: ImportableFile[]): void;
}>();

const userStore = useUserStore();
const { isAnonymous } = storeToRefs(userStore);

const localSelectedItems = ref<ImportableFile[]>(props.selectedItems);

function toggleSelection(item: ImportableFile) {
    const index = localSelectedItems.value.findIndex((selected) => selected.path === item.path);
    if (index === -1) {
        localSelectedItems.value.push(item);
    } else {
        localSelectedItems.value.splice(index, 1);
    }
    emit("update:selectedItems", localSelectedItems.value);
}

const currentListView = computed(() => userStore.currentListViewPreferences.zipFileSelector || "list");

const localFileSizeLimit = computed(() => {
    return props.zipSource instanceof File ? props.bytesLimit : undefined;
});
</script>

<template>
    <div class="zip-file-selector w-100">
        <ListHeader list-id="zipFileSelector" show-view-toggle />

        <div v-if="props.zipContents.workflows.length > 0" class="d-flex flex-column w-100">
            <Heading h3 separator> Workflows </Heading>

            <BAlert v-if="isAnonymous" variant="warning" show fade>You must be logged in to import workflows</BAlert>
            <p>Here you can select workflows compatible with Galaxy and import them into your account.</p>

            <div class="d-flex flex-wrap">
                <ZipFileEntryCard
                    v-for="workflow in props.zipContents.workflows"
                    :key="workflow.path"
                    :file="workflow"
                    :grid-view="currentListView === 'grid'"
                    :selected="localSelectedItems.includes(workflow)"
                    @select="toggleSelection(workflow)" />
            </div>
        </div>

        <div v-if="props.zipContents.files.length > 0" class="d-flex flex-column w-100">
            <Heading h3 separator> Files </Heading>

            <p>Here you can select individual files to import into your <b>current history</b>.</p>

            <div class="d-flex flex-wrap">
                <ZipFileEntryCard
                    v-for="dataset in props.zipContents.files"
                    :key="dataset.path"
                    :file="dataset"
                    :bytes-limit="localFileSizeLimit"
                    :grid-view="currentListView === 'grid'"
                    :selected="localSelectedItems.includes(dataset)"
                    @select="toggleSelection(dataset)" />
            </div>
        </div>
    </div>
</template>
