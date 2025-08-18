<script setup lang="ts">
import { faFile, faNetworkWired } from "@fortawesome/free-solid-svg-icons";
import { computed } from "vue";

import type { CardBadge } from "@/components/Common/GCard.types";
import type { ImportableFile } from "@/composables/zipExplorer";
import { bytesToString } from "@/utils/utils";

import ZipFileEntrySummaryCard from "./ZipFileEntrySummaryCard.vue";
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

const totalFileSize = computed(() => {
    return regularFiles.value.reduce((total, file) => total + file.size, 0);
});

const workflowBadges: CardBadge[] = [
    {
        id: "workflow-count",
        label: `${workflowFiles.value.length} workflow${workflowFiles.value.length > 1 ? "s" : ""}`,
        title: "Number of Workflows to import",
    },
];

const fileBadges: CardBadge[] = [
    {
        id: "file-count",
        label: `${regularFiles.value.length} file${regularFiles.value.length > 1 ? "s" : ""}`,
        title: "Number of Files to import",
    },
    {
        id: "total-size",
        label: bytesToString(totalFileSize.value, true, undefined),
        title: "Total Size of Files to import",
        variant: "info",
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
                title-size="md"
                :title-icon="{ icon: faNetworkWired }"
                :badges="workflowBadges">
                <template v-slot:description>
                    <p v-localize>The following workflows will be imported from the archive into your account.</p>
                    <div class="d-flex flex-wrap">
                        <ZipFileEntrySummaryCard v-for="file in workflowFiles" :key="file.path" :file="file" />
                    </div>
                </template>
            </GCard>

            <GCard
                v-if="regularFiles.length > 0"
                id="zip-files-summary"
                title="Files to Import"
                title-size="md"
                :title-icon="{ icon: faFile }"
                :badges="fileBadges">
                <template v-slot:description>
                    <p v-localize>
                        The following files will be imported from the archive into your
                        <b>currently active Galaxy history</b>.
                    </p>
                    <div class="d-flex flex-wrap">
                        <ZipFileEntrySummaryCard v-for="file in regularFiles" :key="file.path" :file="file" />
                    </div>
                </template>
            </GCard>
        </div>
    </div>
</template>
