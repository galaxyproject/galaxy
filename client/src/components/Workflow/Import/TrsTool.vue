<script setup lang="ts">
import { faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BFormSelect } from "bootstrap-vue";
import { computed, ref } from "vue";

import { useMarkdown } from "@/composables/markdown";

import type { TrsTool, TrsToolVersion } from "./types";

interface Props {
    trsTool: TrsTool;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "onImport", versionId: string): void;
}>();

const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true });

const reversedVersions = computed(() => {
    return [...props.trsTool.versions].reverse();
});

const selectedVersion = ref<TrsToolVersion | null>(
    reversedVersions.value.length > 0 ? reversedVersions.value[0] : null
);

const versionOptions = computed(() => {
    return reversedVersions.value.map((version) => ({
        value: version,
        text: version.name,
    }));
});

function importSelectedVersion() {
    if (selectedVersion.value) {
        const version_id = selectedVersion.value.id.includes(`:${selectedVersion.value.name}`)
            ? selectedVersion.value.name
            : selectedVersion.value.id;
        emit("onImport", version_id);
    }
}
</script>

<template>
    <div>
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
        <div>
            <b>Versions</b>

            <div class="d-flex align-items-center gap-2 mt-2">
                <BFormSelect
                    v-model="selectedVersion"
                    :options="versionOptions"
                    class="workflow-version-select"
                    style="max-width: 300px" />

                <BButton
                    class="workflow-import"
                    :disabled="!selectedVersion"
                    @click="importSelectedVersion">
                    Import

                    <FontAwesomeIcon :icon="faUpload" />
                </BButton>
            </div>
        </div>
    </div>
</template>
