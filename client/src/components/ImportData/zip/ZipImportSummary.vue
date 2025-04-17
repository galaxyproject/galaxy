<script setup lang="ts">
import { faFile, faNetworkWired } from "@fortawesome/free-solid-svg-icons";
import { computed } from "vue";

import { type ImportableFile } from "@/composables/zipExplorer";
import { bytesToString } from "@/utils/utils";

import GCard from "@/components/Common/GCard.vue";

interface Props {
    filesToImport: ImportableFile[];
}

const props = defineProps<Props>();

const workflowFiles = computed(() => {
    return props.filesToImport.filter((file) => file.type === "workflow");
});

const regularFiles = computed(() => {
    return props.filesToImport.filter((file) => file.type === "file");
});

function fileToIcon(file: ImportableFile) {
    return file.type === "workflow" ? faNetworkWired : faFile;
}

const workflowBadges = [
    {
        id: "workflow-count",
        label: `${workflowFiles.value.length} workflow${workflowFiles.value.length > 1 ? "s" : ""}`,
        title: "Number of Workflows to import",
        visible: true,
    },
];

const fileBadges = [
    {
        id: "file-count",
        label: `${regularFiles.value.length} file${regularFiles.value.length > 1 ? "s" : ""}`,
        title: "Number of Files to import",
        visible: true,
    },
    {
        id: "total-size",
        label: bytesToString(
            regularFiles.value.reduce((total, file) => total + file.size, 0),
            true,
            undefined
        ),
        title: "Total Size of Files to import",
        variant: "info",
        visible: true,
    },
];
</script>

<template>
    <div class="w-100">
        <div class="d-flex flex-grow-1">
            <GCard
                v-if="workflowFiles.length > 0"
                id="zip-workflows-summary"
                title="Workflows to Import"
                :badges="workflowBadges">
                <template v-slot:description>
                    <p v-localize>The following workflows will be imported from the ZIP file into your account.</p>
                    <div class="d-flex flex-wrap">
                        <GCard
                            v-for="file in workflowFiles"
                            :id="file.path"
                            :key="file.path"
                            :title="file.name"
                            :icon="fileToIcon(file)"
                            class="zip-file-summary-card">
                            <template v-slot:description>
                                <div v-if="file.path !== file.name" class="zip-file-path text-muted">
                                    {{ file.path }}
                                </div>
                                <div v-if="file.description">{{ file.description }}</div>
                            </template>
                        </GCard>
                    </div>
                </template>
            </GCard>

            <GCard v-if="regularFiles.length > 0" id="zip-files-summary" title="Files to Import" :badges="fileBadges">
                <template v-slot:description>
                    <p v-localize>
                        The following files will be imported from the ZIP file into your
                        <b>currently active Galaxy history</b>.
                    </p>
                    <div class="d-flex flex-wrap">
                        <GCard
                            v-for="file in regularFiles"
                            :id="file.path"
                            :key="file.path"
                            :title="file.name"
                            :icon="fileToIcon(file)"
                            class="zip-file-summary-card">
                            <template v-slot:description>
                                <div v-if="file.path !== file.name" class="zip-file-path text-muted">
                                    {{ file.path }}
                                </div>
                                <div v-if="file.description">{{ file.description }}</div>
                            </template>
                        </GCard>
                    </div>
                </template>
            </GCard>
        </div>
    </div>
</template>
