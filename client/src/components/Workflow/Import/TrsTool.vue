<script setup lang="ts">
import { faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BFormSelect } from "bootstrap-vue";
import { computed, onMounted, ref, watch } from "vue";

import { useMarkdown } from "@/composables/markdown";

import type { TrsTool, TrsToolVersion } from "./types";

interface Props {
    trsTool: TrsTool;
    mode?: "modal" | "wizard";
}

const props = withDefaults(defineProps<Props>(), {
    mode: "modal",
});

const emit = defineEmits<{
    (e: "onImport", versionId: string): void;
    (e: "onSelect", versionId: string): void;
}>();

const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true });

const reversedVersions = computed(() => {
    return [...props.trsTool.versions].reverse();
});

const selectedVersion = ref<TrsToolVersion | null>(
    reversedVersions.value.length > 0 ? (reversedVersions.value[0] ?? null) : null,
);

const versionOptions = computed(() => {
    return reversedVersions.value.map((version) => ({
        value: version,
        text: version.name,
    }));
});

// In modal mode: show import button and allow manual import
// In wizard mode: hide import button and emit onSelect when version changes
const showImportButton = computed(() => props.mode === "modal");

// Watch for version changes in wizard mode to emit selection
watch(selectedVersion, (newVersion) => {
    if (newVersion && props.mode === "wizard") {
        const version_id = newVersion.id.includes(`:${newVersion.name}`) ? newVersion.name : newVersion.id;
        emit("onSelect", version_id);
    }
});

// Emit initial selection in wizard mode
onMounted(() => {
    if (props.mode === "wizard" && selectedVersion.value) {
        const version_id = selectedVersion.value.id.includes(`:${selectedVersion.value.name}`)
            ? selectedVersion.value.name
            : selectedVersion.value.id;
        emit("onSelect", version_id);
    }
});

function importSelectedVersion() {
    const version = selectedVersion.value;
    if (version) {
        const version_id = version.id.includes(`:${version.name}`) ? version.name : version.id;
        emit("onImport", version_id);
    }
}
</script>

<template>
    <div>
        <div class="mb-3">
            <b>Select a version</b>

            <div class="d-flex align-items-center gap-2 mt-2">
                <BFormSelect
                    v-model="selectedVersion"
                    :options="versionOptions"
                    class="workflow-version-select"
                    style="max-width: 300px" />

                <BButton
                    v-if="showImportButton"
                    class="workflow-import"
                    :disabled="!selectedVersion"
                    @click="importSelectedVersion">
                    Import

                    <FontAwesomeIcon :icon="faUpload" />
                </BButton>
            </div>
        </div>
        <div>
            <b>Name:</b>

            <span>{{ props.trsTool.name }}</span>
        </div>
        <div>
            <b>Description:</b>

            <span v-html="renderMarkdown(props.trsTool.description)" />
        </div>
        <div>
            <b>Organization</b>

            <span>{{ props.trsTool.organization }}</span>
        </div>
    </div>
</template>
