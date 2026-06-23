<script setup lang="ts">
import { faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BFormSelect } from "bootstrap-vue";
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

/** Parse a version string like "v1.2.3" into numeric parts, or null if not semver-like. */
function parseSemver(name: string): number[] | null {
    const match = name.match(/(\d+)(?:\.(\d+))?(?:\.(\d+))?/);
    if (!match) {
        return null;
    }
    return [
        parseInt(match[1] as string, 10),
        match[2] !== undefined ? parseInt(match[2], 10) : 0,
        match[3] !== undefined ? parseInt(match[3], 10) : 0,
    ];
}

/** Compare two parsed semver arrays in descending order. */
function compareSemverDesc(a: number[], b: number[]): number {
    for (let i = 0; i < 3; i++) {
        if ((a[i] as number) !== (b[i] as number)) {
            return (b[i] as number) - (a[i] as number);
        }
    }
    return 0;
}

const sortedVersions = computed(() => {
    return props.trsTool.versions.slice().sort((a, b) => {
        const aParsed = parseSemver(a.name);
        const bParsed = parseSemver(b.name);

        if (aParsed && bParsed) {
            return compareSemverDesc(aParsed, bParsed);
        } else if (aParsed) {
            return -1;
        } else if (bParsed) {
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
