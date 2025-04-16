<script setup lang="ts">
import { faFile, faNetworkWired } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
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
import ZipPreview from "./ZipPreview.vue";
import ZipSelector from "./ZipSelector.vue";
import Heading from "@/components/Common/Heading.vue";
import GenericWizard from "@/components/Common/Wizard/GenericWizard.vue";

const router = useRouter();

const { importArtifacts, isZipArchiveAvailable, zipExplorer, reset: resetExplorer, isValidUrl } = useZipExplorer();

const { currentHistoryId } = storeToRefs(useHistoryStore());

const isWizardBusy = ref<boolean>(false);
const errorMessage = ref<string>();

const importableZipContents = ref<ImportableZipContents>();

const filesToImport = ref<ImportableFile[]>([]);
const zipSource = ref<File | string>();

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
        label: "Preview ZIP archive",
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

function fileToIcon(file: ImportableFile) {
    return file.type === "workflow" ? faNetworkWired : faFile;
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
    console.log("onZipSourceChanged", source);

    errorMessage.value = undefined;
    resetExplorer();
    zipSource.value = source;
    if (source) {
        // Skip the next button if the source is a local file
        if (source instanceof File) {
            wizard.goTo("zip-file-preview");
        }
    } else {
        errorMessage.value = "Invalid ZIP source.";
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
            title="Import individual files from Zip"
            :use="wizard"
            submit-button-label="Import"
            :is-busy="isWizardBusy"
            @submit="importItems">
            <template v-slot:header>
                <Heading h1 separator inline size="md">Import Files from Zip</Heading>
            </template>

            <ZipSelector v-if="wizard.isCurrent('zip-file-selector')" @zipSourceChanged="onZipSourceChanged" />

            <ZipPreview v-if="wizard.isCurrent('zip-file-preview') && zipSource" :zip-source="zipSource" />

            <ZipFileSelector
                v-if="wizard.isCurrent('select-items') && importableZipContents"
                :zip-contents="importableZipContents"
                :selected-items="filesToImport"
                @update:selectedItems="onSelectionUpdate" />

            <div v-else-if="wizard.isCurrent('import-summary')">
                <div>
                    <ul>
                        <li v-for="item in filesToImport" :key="item.path">
                            <FontAwesomeIcon :icon="fileToIcon(item)" :title="`This is a ${item.type}`" />
                            {{ item.name }}
                        </li>
                    </ul>
                </div>
            </div>
        </GenericWizard>
    </div>
</template>
