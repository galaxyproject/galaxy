<script setup lang="ts">
import { faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, onMounted, ref, watch } from "vue";

import { useMarkdown } from "@/composables/markdown";

import { sortTrsVersions, trsVersionId } from "./trsVersion";
import type { TrsTool, TrsToolVersion } from "./types";

import GButton from "@/components/BaseComponents/GButton.vue";
import GSelect from "@/components/BaseComponents/GSelect.vue";

interface Props {
    trsTool: TrsTool;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "onImport", versionId: string): void;
    (e: "onSelect", versionId: string): void;
}>();

const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true });

const sortedVersions = computed(() => sortTrsVersions(props.trsTool.versions));

const selectedVersion = ref<TrsToolVersion | null>(
    sortedVersions.value.length > 0 ? (sortedVersions.value[0] ?? null) : null,
);

const versionOptions = computed(() => {
    return sortedVersions.value.map((version) => ({
        value: version,
        text: version.name,
    }));
});

// Hide import button in wizard mode
const showImportButton = computed(() => false);

// Watch for version changes in wizard mode to emit selection
watch(selectedVersion, (newVersion) => {
    if (newVersion) {
        emit("onSelect", trsVersionId(newVersion));
    }
});

// Emit initial selection in wizard mode
onMounted(() => {
    if (selectedVersion.value) {
        emit("onSelect", trsVersionId(selectedVersion.value));
    }
});

function importSelectedVersion() {
    const version = selectedVersion.value;
    if (version) {
        emit("onImport", trsVersionId(version));
    }
}
</script>

<template>
    <div>
        <div class="mb-3">
            <b>Select a version</b>

            <div class="d-flex align-items-center gap-2 mt-2">
                <GSelect
                    v-model="selectedVersion"
                    aria-label="Select a version"
                    class="workflow-version-select"
                    style="max-width: 300px"
                    :options="versionOptions" />

                <GButton
                    v-if="showImportButton"
                    class="workflow-import"
                    :disabled="!selectedVersion"
                    @click="importSelectedVersion">
                    Import
                    <FontAwesomeIcon :icon="faUpload" />
                </GButton>
            </div>
        </div>
        <div>
            <b>Name:</b>

            <span>{{ props.trsTool.name }}</span>
        </div>
        <div>
            <b>Description:</b>

            <span v-sanitize-html:links="renderMarkdown(props.trsTool.description)" />
        </div>
        <div>
            <b>Organization</b>

            <span>{{ props.trsTool.organization }}</span>
        </div>
    </div>
</template>
