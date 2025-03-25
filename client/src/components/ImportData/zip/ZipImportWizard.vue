<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";

import { useWizard } from "@/components/Common/Wizard/useWizard";
import { type ImportableZipContents, useZipExplorer, type ZipContentFile } from "@/composables/zipExplorer";
import { errorMessageAsString } from "@/utils/simple-error";

import ZipFileSelector from "./ZipFileSelector.vue";
import GenericWizard from "@/components/Common/Wizard/GenericWizard.vue";

const { getImportableZipContents, importArtifacts, isZipArchiveAvailable } = useZipExplorer();

const isWizardBusy = ref<boolean>(false);
const errorMessage = ref<string>();

interface ImportData {
    filesToImport: ZipContentFile[];
}

const importableZipContents = ref<ImportableZipContents>();

const importData = reactive<ImportData>({
    filesToImport: [],
});

const wizard = useWizard({
    "select-items": {
        label: "Select items to import",
        instructions: computed(() => {
            return `Review the contents of the Zip file and select the items you wish to import.`;
        }),
        isValid: () => true,
        isSkippable: () => false,
    },
});

async function importItems() {
    isWizardBusy.value = true;
    try {
        await importArtifacts(importData.filesToImport);
    } catch (error) {
        errorMessage.value = errorMessageAsString(error);
    } finally {
        isWizardBusy.value = false;
    }
}

watch(
    isZipArchiveAvailable,
    (isAvailable) => {
        if (isAvailable) {
            importableZipContents.value = getImportableZipContents();
        } else {
            importableZipContents.value = undefined;
        }
    },
    { immediate: true }
);
</script>

<template>
    <div>
        <GenericWizard
            v-if="importableZipContents"
            class="zip-import-wizard"
            title="Import individual files from Zip"
            :use="wizard"
            submit-button-label="Import"
            :is-busy="isWizardBusy"
            @submit="importItems">
            <div v-if="wizard.isCurrent('select-items')">
                <ZipFileSelector
                    :zip-contents="importableZipContents"
                    :selected-items="importData.filesToImport"
                    @update:selectedItems="importData.filesToImport = $event" />
            </div>
        </GenericWizard>
        <BAlert v-else variant="warning" show>
            There is no Zip archive currently open for import. Please go to Upload and select `Import from Zip` to start
            the import process.
        </BAlert>

        <BAlert v-if="errorMessage" show dismissible fade variant="danger" @dismissed="errorMessage = undefined">
            {{ errorMessage }}
        </BAlert>
    </div>
</template>
