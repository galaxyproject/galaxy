<script setup lang="ts">
import { computed, reactive, ref } from "vue";

import { useWizard } from "@/components/Common/Wizard/useWizard";
import { useZipExplorer, type ZipContentFile } from "@/composables/zipExplorer";
import { errorMessageAsString } from "@/utils/simple-error";

import ZipFileSelector from "./ZipFileSelector.vue";
import GenericWizard from "@/components/Common/Wizard/GenericWizard.vue";

const { getImportableZipContents, importArtifacts } = useZipExplorer();

const isWizardBusy = ref<boolean>(false);
const errorMessage = ref<string>();

interface ImportData {
    filesToImport: ZipContentFile[];
}

const importableZipFiles = getImportableZipContents();

const importData = reactive<ImportData>({
    filesToImport: [],
});

const wizard = useWizard({
    "select-items": {
        label: "Select items to import",
        instructions: computed(() => {
            return `Select the items you wish to import and click Next to continue.`;
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
</script>

<template>
    <div>
        <GenericWizard
            class="zip-import-wizard"
            title="Import from Zip"
            :use="wizard"
            submit-button-label="Import"
            :is-busy="isWizardBusy"
            @submit="importItems">
            <div v-if="wizard.isCurrent('select-items')">
                <ZipFileSelector
                    :workflows="importableZipFiles.workflows"
                    :files="importableZipFiles.files"
                    :selected-items="importData.filesToImport"
                    @update:selectedItems="importData.filesToImport = $event" />
            </div>
        </GenericWizard>
        <BAlert v-if="errorMessage" show dismissible fade variant="danger" @dismissed="errorMessage = undefined">
            {{ errorMessage }}
        </BAlert>
    </div>
</template>
