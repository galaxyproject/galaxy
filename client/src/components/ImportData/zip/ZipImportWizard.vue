<script setup lang="ts">
import { faFile, faNetworkWired } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

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
import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";
import GenericWizard from "@/components/Common/Wizard/GenericWizard.vue";

const { importArtifacts, isZipArchiveAvailable, zipExplorer } = useZipExplorer();

const { currentHistoryId } = storeToRefs(useHistoryStore());

const isWizardBusy = ref<boolean>(false);
const errorMessage = ref<string>();

const importableZipContents = ref<ImportableZipContents>();

const filesToImport = ref<ImportableFile[]>([]);

const wizard = useWizard({
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
        await importArtifacts(filesToImport.value, currentHistoryId.value);
    } catch (error) {
        errorMessage.value = errorMessageAsString(error);
    } finally {
        isWizardBusy.value = false;
    }
}

function resetWizard() {
    filesToImport.value = [];
    wizard.goBackTo("select-items");
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

const breadcrumbItems = computed(() => {
    return [
        {
            title: "Import Files from Zip",
        },
    ];
});
</script>

<template>
    <div>
        <BAlert v-if="errorMessage" show dismissible fade variant="danger" @dismissed="errorMessage = undefined">
            {{ errorMessage }}
        </BAlert>

        <GenericWizard
            v-if="importableZipContents"
            container-component="div"
            class="zip-import-wizard"
            title="Import individual files from Zip"
            :use="wizard"
            submit-button-label="Import"
            :is-busy="isWizardBusy"
            @submit="importItems">
            <template v-slot:header>
                <BreadcrumbHeading :items="breadcrumbItems" />
            </template>

            <ZipFileSelector
                v-if="wizard.isCurrent('select-items')"
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
        <BAlert v-else variant="warning" show>
            There is no Zip archive currently open for import. Please go to <b>Upload</b> and select
            <b>Import from Zip</b> to start the import process.
        </BAlert>
    </div>
</template>
