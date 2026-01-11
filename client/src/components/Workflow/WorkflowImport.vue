<script setup lang="ts">
import { BCard, BCardBody, BCardTitle } from "bootstrap-vue";
import { computed, type Ref, ref } from "vue";
import { useRoute } from "vue-router/composables";

import { useWizard } from "@/components/Common/Wizard/useWizard";
import type { TrsSelection } from "@/components/Workflow/Import/types";
import { Services } from "@/components/Workflow/services";

import GenericWizard from "@/components/Common/Wizard/GenericWizard.vue";
import FromFile from "@/components/Workflow/Import/FromFile.vue";
import FromUrl from "@/components/Workflow/Import/FromUrl.vue";
import TrsImport from "@/components/Workflow/Import/TrsImport.vue";

type ImportMethod = "upload" | "fetch" | "repository";
type TrsMethod = "search" | "url" | "id";

const route = useRoute();
const selectedMethod = ref<ImportMethod | null>(null);
const selectedTrsMethod = ref<TrsMethod | null>(null);
const trsServers: Ref<TrsSelection[]> = ref([]);
const fileComponent = ref<InstanceType<typeof FromFile>>();
const urlComponent = ref<InstanceType<typeof FromUrl>>();
const trsComponent = ref<InstanceType<typeof TrsImport>>();

// Validation states for each step
const uploadValid = ref(false);
const urlValid = ref(false);
const trsSearchValid = ref(false);
const trsUrlValid = ref(false);
const trsIdValid = ref(false);

const queryParams = computed(() => ({
    trsId: route.query.trs_id as string | undefined,
    trsUrl: route.query.trs_url as string | undefined,
    trsServer: route.query.trs_server as string | undefined,
    trsVersionId: route.query.trs_version_id as string | undefined,
    isRun: route.query.run_form === "true",
}));

const services = new Services();
services.getTrsServers().then((res) => {
    trsServers.value = res;
});

// Auto-select method based on query parameters
if (queryParams.value.trsId || queryParams.value.trsServer) {
    selectedMethod.value = "repository";
    selectedTrsMethod.value = "id";
} else if (queryParams.value.trsUrl) {
    selectedMethod.value = "repository";
    selectedTrsMethod.value = "url";
}

const wizard = useWizard({
    "select-method": {
        label: "Select Import Method",
        instructions: "Choose how you would like to import your workflow",
        isValid: () => selectedMethod.value !== null,
        isSkippable: () => false, // Never skip - always allow going back to change method
    },
    "placeholder-select-workflow": {
        label: "Select workflow",
        instructions: "Select a workflow to import",
        isValid: () => selectedMethod.value !== null,
        isSkippable: () => selectedMethod.value !== null, // Hide as soon as method selected
    },
    "upload-file": {
        label: "Upload File",
        instructions: "Upload a workflow file from your computer",
        isValid: () => uploadValid.value,
        isSkippable: () => !selectedMethod.value || selectedMethod.value !== "upload",
    },
    "fetch-url": {
        label: "Fetch URL",
        instructions: "Provide a URL to fetch your workflow",
        isValid: () => urlValid.value,
        isSkippable: () => !selectedMethod.value || selectedMethod.value !== "fetch",
    },
    "select-trs-method": {
        label: "TRS Import Method",
        instructions: "Choose how to import from the TRS repository",
        isValid: () => selectedTrsMethod.value !== null,
        isSkippable: () => !selectedMethod.value || selectedMethod.value !== "repository",
    },
    "trs-search": {
        label: "Search workflows",
        instructions: "Search for workflows in TRS repositories",
        isValid: () => trsSearchValid.value,
        // Not skippable if: in repository mode AND TRS method selected AND search is selected
        isSkippable: () =>
            !(selectedMethod.value === "repository" && selectedTrsMethod.value && selectedTrsMethod.value === "search"),
    },
    "trs-url": {
        label: "Enter TRS URL",
        instructions: "Import from a TRS URL",
        isValid: () => trsUrlValid.value,
        // Not skippable if: in repository mode AND TRS method selected AND url is selected
        isSkippable: () =>
            !(selectedMethod.value === "repository" && selectedTrsMethod.value && selectedTrsMethod.value === "url"),
    },
    "trs-id": {
        label: "Enter TRS ID",
        instructions: "Import using a TRS server and tool ID",
        isValid: () => trsIdValid.value,
        // Not skippable if: in repository mode AND TRS method selected AND id is selected
        isSkippable: () =>
            !(selectedMethod.value === "repository" && selectedTrsMethod.value && selectedTrsMethod.value === "id"),
    },
    "placeholder-select-trs": {
        label: "Select workflow",
        instructions: "Select a workflow to import",
        isValid: () => selectedMethod.value !== null,
        isSkippable: () => !(selectedMethod.value && selectedMethod.value === "repository" && !selectedTrsMethod.value), // Hide as soon as TRS method selected
    },
});

function selectMethod(method: ImportMethod) {
    selectedMethod.value = method;
}

function selectTrsMethod(method: TrsMethod) {
    selectedTrsMethod.value = method;
}

function onSubmit() {
    // Trigger the import on the active child component
    if (selectedMethod.value === "upload" && fileComponent.value) {
        fileComponent.value.attemptImport();
    } else if (selectedMethod.value === "fetch" && urlComponent.value) {
        urlComponent.value.attemptImport();
    } else if (selectedMethod.value === "repository" && trsComponent.value) {
        trsComponent.value.attemptImport();
    }
}

function onUploadValid(e: boolean) {
    uploadValid.value = e;
}

function onUrlValid(e: boolean) {
    urlValid.value = e;
}

function onTrsSearchValid(e: boolean) {
    trsSearchValid.value = e;
}

function onTrsUrlValid(e: boolean) {
    trsUrlValid.value = e;
}

function onTrsIdValid(e: boolean) {
    trsIdValid.value = e;
}
</script>

<template>
    <section>
        <GenericWizard
            :use="wizard"
            title="Import Workflow"
            container-component="div"
            submit-button-label="Import"
            @submit="onSubmit">
            <div v-if="wizard.isCurrent('select-method')" class="method-selection">
                <div class="row mx-auto" style="max-width: 1000px">
                    <div class="col-xl-4 mb-3 mx-auto" style="max-width: 300px">
                        <BCard
                            class="h-100 workflow-import-file-link clickable-card text-center wizard-selection-card"
                            :class="{ selected: selectedMethod === 'upload' }"
                            @click="selectMethod('upload')">
                            <BCardTitle>Upload file</BCardTitle>
                            <BCardBody>
                                <p class="text-muted">
                                    Upload a <code>*.ga</code> file from your computer. These can be downloaded from
                                    Galaxy servers, or from workflow repositories like Dockstore or WorkflowHub.
                                </p>
                            </BCardBody>
                        </BCard>
                    </div>

                    <div class="col-xl-4 mb-3 mx-auto" style="max-width: 300px">
                        <BCard
                            class="h-100 workflow-import-url-link clickable-card text-center wizard-selection-card"
                            :class="{ selected: selectedMethod === 'fetch' }"
                            @click="selectMethod('fetch')">
                            <BCardTitle>Fetch URL</BCardTitle>
                            <BCardBody>
                                <p class="text-muted">
                                    Fetch a remote <code>*.ga</code> file from any publicly accessible URL. These can be
                                    generated by any Galaxy server, or public repositories like GitHub.
                                </p>
                            </BCardBody>
                        </BCard>
                    </div>

                    <div class="col-xl-4 mb-3 mx-auto" style="max-width: 300px">
                        <BCard
                            class="h-100 workflow-import-trs-link clickable-card text-center wizard-selection-card"
                            :class="{ selected: selectedMethod === 'repository' }"
                            @click="selectMethod('repository')">
                            <BCardTitle>Import from repository</BCardTitle>
                            <BCardBody>
                                <p>Import a workflow from a configured GA4GH server:</p>
                                <ul class="text-left text-muted">
                                    <li v-for="server in trsServers" :key="server.id">
                                        {{ server.label }}
                                    </li>
                                </ul>
                            </BCardBody>
                        </BCard>
                    </div>
                </div>
            </div>

            <div v-else-if="wizard.isCurrent('upload-file')" class="import-form">
                <div class="container-narrow">
                    <FromFile ref="fileComponent" mode="wizard" @input-valid="onUploadValid" />
                </div>
            </div>

            <div v-else-if="wizard.isCurrent('fetch-url')" class="import-form">
                <div class="container-narrow">
                    <FromUrl ref="urlComponent" mode="wizard" @input-valid="onUrlValid" />
                </div>
            </div>

            <div v-else-if="wizard.isCurrent('select-trs-method')" class="method-selection">
                <div class="row mx-auto" style="max-width: 1000px">
                    <div class="col-xl-4 mb-3 mx-auto" style="max-width: 300px">
                        <BCard
                            class="h-100 clickable-card text-center wizard-selection-card"
                            :class="{ selected: selectedTrsMethod === 'search' }"
                            @click="selectTrsMethod('search')">
                            <BCardTitle>Search workflow registries</BCardTitle>
                            <BCardBody>
                                <p class="text-muted">Search for workflows across configured GA4GH servers.</p>
                            </BCardBody>
                        </BCard>
                    </div>

                    <div class="col-xl-4 mb-3 mx-auto" style="max-width: 300px">
                        <BCard
                            class="h-100 clickable-card text-center wizard-selection-card"
                            :class="{ selected: selectedTrsMethod === 'url' }"
                            @click="selectTrsMethod('url')">
                            <BCardTitle>TRS URL</BCardTitle>
                            <BCardBody>
                                <p class="text-muted">Import directly from any GA4GH server with a TRS URL.</p>
                            </BCardBody>
                        </BCard>
                    </div>

                    <div class="col-xl-4 mb-3 mx-auto" style="max-width: 300px">
                        <BCard
                            class="h-100 clickable-card text-center wizard-selection-card"
                            :class="{ selected: selectedTrsMethod === 'id' }"
                            @click="selectTrsMethod('id')">
                            <BCardTitle>TRS ID</BCardTitle>
                            <BCardBody>
                                <p class="text-muted">
                                    When you know the TRS ID for a workflow in one of the configured GA4GH servers.
                                </p>
                            </BCardBody>
                        </BCard>
                    </div>
                </div>
            </div>

            <div v-else-if="wizard.isCurrent('trs-search')" class="import-form">
                <div class="container-wide">
                    <TrsImport
                        ref="trsComponent"
                        :trs-servers="trsServers"
                        :is-run="queryParams.isRun"
                        mode="wizard"
                        trs-method="search"
                        @input-valid="onTrsSearchValid" />
                </div>
            </div>

            <div v-else-if="wizard.isCurrent('trs-url')" class="import-form">
                <div class="container-narrow">
                    <TrsImport
                        ref="trsComponent"
                        :trs-servers="trsServers"
                        :is-run="queryParams.isRun"
                        :query-trs-url="queryParams.trsUrl"
                        mode="wizard"
                        trs-method="url"
                        @input-valid="onTrsUrlValid" />
                </div>
            </div>

            <div v-else-if="wizard.isCurrent('trs-id')" class="import-form">
                <div class="container-narrow">
                    <TrsImport
                        ref="trsComponent"
                        :trs-servers="trsServers"
                        :is-run="queryParams.isRun"
                        :query-trs-id="queryParams.trsId"
                        :query-trs-server="queryParams.trsServer"
                        :query-trs-version-id="queryParams.trsVersionId"
                        mode="wizard"
                        trs-method="id"
                        @input-valid="onTrsIdValid" />
                </div>
            </div>
        </GenericWizard>
    </section>
</template>

<style scoped>
.clickable-card {
    cursor: pointer;
    transition:
        transform 0.2s,
        box-shadow 0.2s;
}

.clickable-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.clickable-card.selected {
    border-color: var(--brand-primary, #007bff);
    border-width: 2px;
}

.method-selection {
    width: 100%;
    display: flex;
    justify-content: center;
}

.import-form {
    width: 100%;
    display: flex;
    justify-content: center;
}

.container-narrow {
    width: 100%;
    max-width: 600px;
}

.container-wide {
    width: 100%;
    max-width: min(1000px, 80vw);
}
</style>
