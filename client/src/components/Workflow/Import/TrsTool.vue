<script setup lang="ts">
import { faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BFormSelect } from "bootstrap-vue";
import semver from "semver";
import { computed, onMounted, ref, watch } from "vue";

import { useMarkdown } from "@/composables/markdown";

import type { TrsTool, TrsToolVersion } from "./types";

import GButton from "@/components/BaseComponents/GButton.vue";

interface Props {
    trsTool: TrsTool;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "onImport", versionId: string): void;
    (e: "onSelect", versionId: string): void;
}>();

const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true });

const sortedVersions = computed(() => {
    return props.trsTool.versions.slice().sort((a, b) => {
        const aSemver = semver.coerce(a.name);
        const bSemver = semver.coerce(b.name);

        if (aSemver && bSemver) {
            return semver.rcompare(aSemver, bSemver);
        } else if (aSemver) {
            return -1;
        } else if (bSemver) {
            return 1;
        } else {
            return b.name.localeCompare(a.name);
        }
    });
});

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
        const version_id = newVersion.id.includes(`:${newVersion.name}`) ? newVersion.name : newVersion.id;
        emit("onSelect", version_id);
    }
});

// Emit initial selection in wizard mode
onMounted(() => {
    if (selectedVersion.value) {
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

            <span v-html="renderMarkdown(props.trsTool.description)" />
        </div>
        <div>
            <b>Organization</b>

            <span>{{ props.trsTool.organization }}</span>
        </div>
    </div>
</template>
