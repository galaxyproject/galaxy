<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { useWizard } from "@/components/Common/Wizard/useWizard";
import {
    getImportableFiles,
    type ImportableFile,
    type ImportableZipContents,
    useZipExplorer,
} from "@/composables/zipExplorer";
import { useHistoryStore } from "@/stores/historyStore";
import { errorMessageAsString } from "@/utils/simple-error";

import ZipFileSelector from "./ZipFileSelector.vue";
import ZipImportSummary from "./ZipImportSummary.vue";
import ZipPreview from "./ZipPreview.vue";
import ZipSelector from "./ZipSelector.vue";
import Heading from "@/components/Common/Heading.vue";
import GenericWizard from "@/components/Common/Wizard/GenericWizard.vue";

const router = useRouter();

const { importArtifacts, isZipArchiveAvailable, zipExplorer, reset: resetExplorer, isValidUrl } = useZipExplorer();

const { currentHistoryId } = storeToRefs(useHistoryStore());

const zipSource = ref<File | string>();

const filesToImport = ref<ImportableFile[]>([]);

const importableZipContents = ref<ImportableZipContents>();

const isWizardBusy = ref<boolean>(false);

const errorMessage = ref<string>();

const isValidSource = computed(() => {
    if (zipSource.value) {
        if (typeof zipSource.value === "string") {
            return isValidUrl(zipSource.value);
        } else if (zipSource.value instanceof File) {
            return true;
        }
    }
    return false;
});

const wizard = useWizard({
    "zip-file-selector": {
        label: "Select ZIP archive",
        instructions: computed(() => {
            return `Please select either a local file or a URL to a ZIP archive to proceed.`;
        }),
        isValid: () => isValidSource.value,
        isSkippable: () => false,
    },
    "zip-file-preview": {
        label: "Preview Contents",
        instructions: computed(() => {
            return `Here you can preview the contents of the ZIP archive. You can go back to select a different ZIP archive if needed or proceed to select the items you want to import in the next step.`;
        }),
        isValid: () => Boolean(zipExplorer.value),
        isSkippable: () => false,
    },
    "select-items": {
        label: "Select items to import",
        instructions: computed(() => {
            return `Review the contents of the Zip archive and select the items you wish to extract and import:`;
        }),
        isValid: () => isAnythingSelected(),
        isSkippable: () => false,
    },
    "import-summary": {
        label: "Summary",
        instructions: computed(() => {
            return `Review your selections before starting the import process:`;
        }),
        isValid: () => true,
        isSkippable: () => false,
    },
});

async function importItems() {
    isWizardBusy.value = true;
    try {
        router.push({ name: "ZipImportResults" });
        await importArtifacts(filesToImport.value, currentHistoryId.value);
    } catch (error) {
        errorMessage.value = errorMessageAsString(error);
    } finally {
        isWizardBusy.value = false;
    }
}

function resetWizard() {
    filesToImport.value = [];
}

function isAnythingSelected() {
    return filesToImport.value.length > 0;
}

function onSelectionUpdate(selectedItems: ImportableFile[]) {
    filesToImport.value = selectedItems;
}

watch(
    [isZipArchiveAvailable, zipExplorer],
    (isAvailable) => {
        if (isAvailable && zipExplorer.value) {
            const contents = getImportableFiles(zipExplorer.value);
            importableZipContents.value = {
                workflows: contents.filter((file) => file.type === "workflow"),
                files: contents.filter((file) => file.type === "file"),
            };
        } else {
            importableZipContents.value = undefined;
        }
        resetWizard();
    },
    { immediate: true }
);

async function onZipSourceChanged(source?: File | string) {
    errorMessage.value = undefined;
    resetExplorer();
    zipSource.value = source;
    if (source) {
        // Skip the next button if the source is a local file
        if (source instanceof File) {
            wizard.goTo("zip-file-preview");
        }
    }
}
</script>

<template>
    <div>
        <BAlert v-if="errorMessage" show dismissible fade variant="danger" @dismissed="errorMessage = undefined">
            {{ errorMessage }}
        </BAlert>

        <GenericWizard
            container-component="div"
            class="zip-import-wizard"
            submit-button-label="Import"
            description="You can import **individual files** directly from a .zip archive —whether it's stored on your local machine 🖥️ or hosted remotely 🌐— **without needing to fully extract, download, or upload the entire archive**. Follow the steps below to get started:"
            :use="wizard"
            :is-busy="isWizardBusy"
            @submit="importItems">
            <template v-slot:header>
                <Heading h1 separator inline size="md">Import individual files from Zip</Heading>
            </template>

            <ZipSelector
                v-if="wizard.isCurrent('zip-file-selector')"
                :zip-source="zipSource"
                @zipSourceChanged="onZipSourceChanged" />

            <ZipPreview v-if="wizard.isCurrent('zip-file-preview') && zipSource" :zip-source="zipSource" />

            <ZipFileSelector
                v-if="wizard.isCurrent('select-items') && importableZipContents"
                :zip-contents="importableZipContents"
                :selected-items="filesToImport"
                @update:selectedItems="onSelectionUpdate" />

            <ZipImportSummary v-if="wizard.isCurrent('import-summary')" :files-to-import="filesToImport" />
        </GenericWizard>
    </div>
</template>
