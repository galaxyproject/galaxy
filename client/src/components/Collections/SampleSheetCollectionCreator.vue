<script lang="ts" setup>
import { useConfig } from "@/composables/config";

import SampleSheetWizard from "./SampleSheetWizard.vue";

const { config, isConfigLoaded } = useConfig();

interface Props {
    fileSourcesConfigured: boolean;
    ftpUploadSite?: string;
}

defineProps<Props>();

/*
const initialElements = [
    ["https://zenodo.org/records/3263975/files/DRR000770.fastqsanger.gz", 1, "treatment1", false],
    ["https://zenodo.org/records/3263975/files/DRR000771.fastqsanger.gz", 2, "treatment1", false],
    ["https://zenodo.org/records/3263975/files/DRR000772.fastqsanger.gz", 1, "none", true],
    ["https://zenodo.org/records/3263975/files/DRR000773.fastqsanger.gz", 1, "treatment2", false],
    ["https://zenodo.org/records/3263975/files/DRR000774.fastqsanger.gz", 2, "treatment3", false],
];
*/

const columnDefinitions = [
    { name: "replicate number", type: "int", description: "The replicate number of this sample." },
    {
        name: "treatment",
        type: "string",
        restrictions: ["treatment1", "treatment2", "none"],
        description: "The treatment code for this sample.",
    },
    {
        name: "is control?",
        type: "boolean",
        description: "Was this sample a control? If TRUE, please ensure treatment is set to none.",
    },
];
</script>

<template>
    <div class="sample-sheet-collection-creator">
        <SampleSheetWizard
            v-if="isConfigLoaded"
            :file-sources-configured="config.file_sources_configured"
            :ftp-upload-site="config.ftp_upload_site"
            :column-definitions="columnDefinitions" />
        <!--
        <SampleSheetGrid :initial-elements="initialElements" :columnDefinitions="columnDefinitions" />
        -->
    </div>
</template>
