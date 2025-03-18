<script setup lang="ts">
import { type ROCrateZipExplorer, type ZipArchive, type ZipFileEntry } from "ro-crate-zip-explorer";
import { computed, ref } from "vue";

import { useWizard } from "@/components/Common/Wizard/useWizard";

import ZipFileSelector from "./ZipFileSelector.vue";
import GenericWizard from "@/components/Common/Wizard/GenericWizard.vue";

interface Props {
    zipExplorer: ROCrateZipExplorer;
}

const props = defineProps<Props>();

const isWizardBusy = ref<boolean>(false);
const errorMessage = ref<string>();

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
    console.log("Importing items");
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
                <ZipFileSelector />
            </div>
        </GenericWizard>
        <BAlert v-if="errorMessage" show dismissible fade variant="danger" @dismissed="errorMessage = undefined">
            {{ errorMessage }}
        </BAlert>
    </div>
</template>
