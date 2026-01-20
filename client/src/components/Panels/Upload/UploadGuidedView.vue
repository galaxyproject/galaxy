<script setup lang="ts">
import { faCompass } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BCard, BCardGroup, BCardTitle } from "bootstrap-vue";
import { ref } from "vue";
import { useRouter } from "vue-router/composables";

import { useWizard } from "@/components/Common/Wizard/useWizard";
import { borderVariant } from "@/components/Common/Wizard/utils";

import type { UploadMethod } from "./types";

import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";
import GenericWizard from "@/components/Common/Wizard/GenericWizard.vue";

const router = useRouter();
const breadcrumbItems = [{ title: "Import Data", to: "/upload" }, { title: "Guided Import Wizard" }];

// Wizard state
const selectedDataLocation = ref<string | null>(null);
const selectedDataType = ref<string | null>(null);
const recommendedMethod = ref<UploadMethod | null>(null);

const wizard = useWizard({
    "data-location": {
        label: "Data Location",
        instructions: "Where is your data currently located?",
        isValid: () => Boolean(selectedDataLocation.value),
        isSkippable: () => false,
    },
    "data-type": {
        label: "Data Type",
        instructions: "What type of data are you importing?",
        isValid: () => Boolean(selectedDataType.value),
        isSkippable: () => false,
    },
    recommendation: {
        label: "Recommended Method",
        instructions: "Based on your answers, we recommend the following import method:",
        isValid: () => Boolean(recommendedMethod.value),
        isSkippable: () => false,
    },
});

function determineRecommendedMethod() {
    // Placeholder logic for determining the recommended method
    // This will be implemented based on the user's answers
    if (selectedDataLocation.value === "local") {
        if (selectedDataType.value === "compressed") {
            recommendedMethod.value = "explore-zip";
        } else {
            recommendedMethod.value = "local-file";
        }
    } else if (selectedDataLocation.value === "remote-url") {
        recommendedMethod.value = "paste-links";
    } else if (selectedDataLocation.value === "remote-files") {
        recommendedMethod.value = "remote-files";
    } else if (selectedDataLocation.value === "data-library") {
        recommendedMethod.value = "data-library";
    } else {
        recommendedMethod.value = "local-file";
    }
}

function selectDataLocation(location: string) {
    selectedDataLocation.value = location;
    if (wizard.isCurrent("data-location")) {
        wizard.goToNext();
    }
}

function selectDataType(type: string) {
    selectedDataType.value = type;
    determineRecommendedMethod();
    if (wizard.isCurrent("data-type")) {
        wizard.goToNext();
    }
}

function proceedWithMethod() {
    if (recommendedMethod.value) {
        router.push(`/upload/${recommendedMethod.value}`);
    }
}
</script>

<template>
    <div class="upload-guided-view d-flex flex-column h-100">
        <BreadcrumbHeading :items="breadcrumbItems">
            <template v-slot:icon>
                <FontAwesomeIcon :icon="faCompass" class="mr-1" />
            </template>
        </BreadcrumbHeading>

        <div class="flex-grow-1 overflow-auto p-3">
            <GenericWizard
                container-component="div"
                submit-button-label="Use This Method"
                description="This wizard will help you choose the best method to import your data into Galaxy. Answer a few simple questions, and we'll recommend the most appropriate import method for your needs."
                :use="wizard"
                @submit="proceedWithMethod">
                <!-- Step 1: Data Location -->
                <BCardGroup v-if="wizard.isCurrent('data-location')" deck>
                    <BCard
                        class="wizard-selection-card"
                        :border-variant="borderVariant(selectedDataLocation === 'local')"
                        @click="selectDataLocation('local')">
                        <BCardTitle>
                            <b>💻 On My Computer</b>
                        </BCardTitle>
                        <div>Files stored on your local device</div>
                    </BCard>
                    <BCard
                        class="wizard-selection-card"
                        :border-variant="borderVariant(selectedDataLocation === 'remote-url')"
                        @click="selectDataLocation('remote-url')">
                        <BCardTitle>
                            <b>🌐 Remote URL</b>
                        </BCardTitle>
                        <div>Files available via HTTP/HTTPS/FTP URLs</div>
                    </BCard>
                    <BCard
                        class="wizard-selection-card"
                        :border-variant="borderVariant(selectedDataLocation === 'remote-files')"
                        @click="selectDataLocation('remote-files')">
                        <BCardTitle>
                            <b>☁️ Remote File Source</b>
                        </BCardTitle>
                        <div>Files from configured remote sources (e.g., S3, cloud storage)</div>
                    </BCard>
                    <BCard
                        class="wizard-selection-card"
                        :border-variant="borderVariant(selectedDataLocation === 'data-library')"
                        @click="selectDataLocation('data-library')">
                        <BCardTitle>
                            <b>📚 Data Library</b>
                        </BCardTitle>
                        <div>Files from Galaxy's shared data library</div>
                    </BCard>
                </BCardGroup>

                <!-- Step 2: Data Type -->
                <BCardGroup v-if="wizard.isCurrent('data-type')" deck>
                    <BCard
                        class="wizard-selection-card"
                        :border-variant="borderVariant(selectedDataType === 'single')"
                        @click="selectDataType('single')">
                        <BCardTitle>
                            <b>📄 Single File</b>
                        </BCardTitle>
                        <div>I want to import one file</div>
                    </BCard>
                    <BCard
                        class="wizard-selection-card"
                        :border-variant="borderVariant(selectedDataType === 'multiple')"
                        @click="selectDataType('multiple')">
                        <BCardTitle>
                            <b>📁 Multiple Files</b>
                        </BCardTitle>
                        <div>I want to import several files at once</div>
                    </BCard>
                    <BCard
                        class="wizard-selection-card"
                        :border-variant="borderVariant(selectedDataType === 'compressed')"
                        @click="selectDataType('compressed')">
                        <BCardTitle>
                            <b>🗜️ Compressed Archive</b>
                        </BCardTitle>
                        <div>My data is in a ZIP or compressed archive</div>
                    </BCard>
                    <BCard
                        class="wizard-selection-card"
                        :border-variant="borderVariant(selectedDataType === 'paste')"
                        @click="selectDataType('paste')">
                        <BCardTitle>
                            <b>📋 Text Content</b>
                        </BCardTitle>
                        <div>I want to paste file content directly</div>
                    </BCard>
                </BCardGroup>

                <!-- Step 3: Recommendation -->
                <BCard v-if="wizard.isCurrent('recommendation')" border-variant="primary">
                    <BCardTitle>
                        <b>We recommend:</b>
                    </BCardTitle>
                    <div v-if="recommendedMethod === 'local-file'">
                        <strong>Upload from Computer</strong><br />
                        Select and upload files from your local device.
                    </div>
                    <div v-else-if="recommendedMethod === 'paste-links'">
                        <strong>Paste Links/URLs</strong><br />
                        Paste URLs to fetch and import data from remote sources.
                    </div>
                    <div v-else-if="recommendedMethod === 'remote-files'">
                        <strong>Choose Remote Files</strong><br />
                        Select files from configured remote file sources.
                    </div>
                    <div v-else-if="recommendedMethod === 'explore-zip'">
                        <strong>Explore Compressed Archive</strong><br />
                        Browse and select files from a compressed zip archive.
                    </div>
                    <div v-else-if="recommendedMethod === 'data-library'">
                        <strong>Import from Data Library</strong><br />
                        Select files from Galaxy's shared data library.
                    </div>
                    <div v-else>
                        <strong>Upload from Computer</strong><br />
                        Select and upload files from your local device.
                    </div>
                    <p class="text-muted mt-3 mb-0">
                        Click "Use This Method" to proceed with the recommended import method, or go back to change your
                        answers.
                    </p>
                </BCard>
            </GenericWizard>
        </div>
    </div>
</template>

<style lang="scss" scoped>
.upload-guided-view {
    background: var(--masthead-bg);
}
</style>
