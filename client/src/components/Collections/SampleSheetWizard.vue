<script setup lang="ts">
import { BCardGroup } from "bootstrap-vue";
import { computed, ref } from "vue";

import { type SampleSheetColumnDefinitions } from "@/api";
import { useWizard } from "@/components/Common/Wizard/useWizard";

import { type RulesSourceFrom } from "./wizard/types";
import { useFileSetSources } from "./wizard/useFileSetSources";

import SampleSheetGrid from "./sheet/SampleSheetGrid.vue";
import PasteData from "./wizard/PasteData.vue";
import SelectDataset from "./wizard/SelectDataset.vue";
import SelectFolder from "./wizard/SelectFolder.vue";
import SourceFromCollection from "./wizard/SourceFromCollection.vue";
import SourceFromDatasetAsTable from "./wizard/SourceFromDatasetAsTable.vue";
import SourceFromPastedData from "./wizard/SourceFromPastedData.vue";
import SourceFromRemoteFiles from "./wizard/SourceFromRemoteFiles.vue";
import GenericWizard from "@/components/Common/Wizard/GenericWizard.vue";

const isBusy = ref<boolean>(false);
const { pasteData, tabularDatasetContents, uris, setRemoteFilesFolder, onFtp, setDatasetContents, setPasteTable } =
    useFileSetSources(isBusy);

interface Props {
    fileSourcesConfigured: boolean;
    ftpUploadSite?: string;
    columnDefinitions: SampleSheetColumnDefinitions;
}

defineProps<Props>();

const sourceInstructions = computed(() => {
    return `Sample sheets can be initialized from a set or files, URIs, or existing datasets.`;
});

const sourceFrom = ref<RulesSourceFrom>("remote_files");

function setSourceForm(newValue: RulesSourceFrom) {
    sourceFrom.value = newValue;
}

const targetCollectionId = ref<string | undefined>(undefined);

const wizard = useWizard({
    "select-source": {
        label: "Select source",
        instructions: sourceInstructions,
        isValid: () => true,
        isSkippable: () => false,
    },
    "select-remote-files-folder": {
        label: "Select folder",
        instructions: "Select folder of files to import.",
        isValid: () => sourceFrom.value === "remote_files" && Boolean(uris.value.length > 0),
        isSkippable: () => sourceFrom.value !== "remote_files",
    },
    "paste-data": {
        label: "Paste data",
        instructions: "Paste data containing URIs and optional extra metadata.",
        isValid: () => sourceFrom.value === "pasted_table" && pasteData.value.length > 0,
        isSkippable: () => sourceFrom.value !== "pasted_table",
    },
    "select-dataset": {
        label: "Select dataset",
        instructions: "Select tabular dataset to load URIs and metadata from.",
        isValid: () => sourceFrom.value === "dataset_as_table" && tabularDatasetContents.value.length > 0,
        isSkippable: () => sourceFrom.value !== "dataset_as_table",
    },
    "select-collection": {
        label: "Select collection",
        instructions: "Select existing collection to transform into a sample sheet.",
        isValid: () => sourceFrom.value === "collection" && Boolean(targetCollectionId.value),
        isSkippable: () => sourceFrom.value !== "collection",
    },
    "fill-grid": {
        label: "Fill sheet",
        instructions: "Fill in metadata to describe the files you're importing.",
        isValid: () => true,
        isSkippable: () => false,
    },
});

const importButtonLabel = computed(() => {
    if (sourceFrom.value == "collection") {
        return "Build";
    } else {
        return "Import";
    }
});

const emit = defineEmits(["dismiss"]);

const initialElements = computed<string[]>(() => {
    if (sourceFrom.value == "remote_files") {
        const rows: string[] = [];
        for (const uri of uris.value) {
            rows.push(uri.uri);
        }
        return rows;
    }
    return [];
});

function submit() {
    emit("dismiss");
}
</script>

<template>
    <GenericWizard :use="wizard" :submit-button-label="importButtonLabel" @submit="submit">
        <div v-if="wizard.isCurrent('select-source')">
            <BCardGroup deck>
                <SourceFromRemoteFiles :selected="sourceFrom === 'remote_files'" @select="setSourceForm" />
                <SourceFromPastedData :selected="sourceFrom === 'pasted_table'" @select="setSourceForm" />
                <SourceFromDatasetAsTable :selected="sourceFrom === 'dataset_as_table'" @select="setSourceForm" />
                <SourceFromCollection :selected="sourceFrom === 'collection'" @select="setSourceForm" />
            </BCardGroup>
        </div>
        <div v-else-if="wizard.isCurrent('paste-data')">
            <PasteData @onChange="setPasteTable" />
        </div>
        <div v-else-if="wizard.isCurrent('select-remote-files-folder')">
            <SelectFolder :ftp-upload-site="ftpUploadSite" @onChange="setRemoteFilesFolder" @onFtp="onFtp" />
        </div>
        <div v-else-if="wizard.isCurrent('select-dataset')">
            <SelectDataset @onChange="setDatasetContents" />
        </div>
        <div v-else-if="wizard.isCurrent('select-collection')">
            <SelectDataset @onChange="setDatasetContents" />
        </div>
        <div v-else-if="wizard.isCurrent('fill-grid')">
            <SampleSheetGrid
                :column-definitions="columnDefinitions"
                :initial-elements="initialElements"
                height="300px" />
        </div>
    </GenericWizard>
</template>
