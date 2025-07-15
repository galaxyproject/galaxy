<script setup lang="ts">
import { BAlert, BCard, BCardGroup, BCardTitle, BFormCheckbox, BFormGroup, BFormInput } from "bootstrap-vue";
import { computed, reactive, ref, watch } from "vue";

import { AVAILABLE_EXPORT_FORMATS } from "@/api/histories.export";
import { useWizard } from "@/components/Common/Wizard/useWizard";
import { borderVariant } from "@/components/Common/Wizard/utils";
import { useFileSources } from "@/composables/fileSources";
import { useMarkdown } from "@/composables/markdown";
import { DEFAULT_EXPORT_PARAMS } from "@/composables/shortTermStorage";

import type { HistoryExportData, HistoryExportDestination } from "./types";

import RDMCredentialsInfo from "@/components/Common/RDMCredentialsInfo.vue";
import RDMDestinationSelector from "@/components/Common/RDMDestinationSelector.vue";
import GenericWizard from "@/components/Common/Wizard/GenericWizard.vue";
import ExternalLink from "@/components/ExternalLink.vue";
import FilesInput from "@/components/FilesDialog/FilesInput.vue";
import FileSourceNameSpan from "@/components/FileSources/FileSourceNameSpan.vue";

const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true });

const { hasWritable: hasWritableFileSources } = useFileSources({ exclude: ["rdm"] });
const {
    hasWritable: hasWritableRDMFileSources,
    getFileSourceById,
    getFileSourcesByType,
    isPrivateFileSource,
} = useFileSources({ include: ["rdm"] });

const resource = "history";

interface ExportDestinationInfo {
    destination: HistoryExportDestination;
    label: string;
    markdownDescription: string;
}

interface Props {
    historyId: string;
    historyName: string;
    isBusy: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "onExport", exportData: HistoryExportData): void;
}>();

const errorMessage = ref<string>();
const exportData: HistoryExportData = reactive(initializeExportData());

const defaultFileName = computed(() => `(Galaxy History) ${props.historyName}`);

const exportButtonLabel = computed(() => {
    switch (exportData.destination) {
        case "download":
            return "Generate Download Link";
        case "remote-source":
            return "Export to Remote Source";
        case "rdm-repository":
            return "Export to RDM Repository";
        case "zenodo-repository":
            return "Export to Zenodo";
        default:
            return "Export";
    }
});

const needsFileName = computed(
    () =>
        exportData.destination === "remote-source" ||
        exportData.destination === "rdm-repository" ||
        exportData.destination === "zenodo-repository"
);

const exportDestinationSummary = computed(() => {
    const exportDestination = exportDestinationTargets.value.find(
        (target) => target.destination === exportData.destination
    );
    return exportDestination?.label ?? "Unknown Destination";
});

const exportDestinationTargets = computed(initializeExportDestinations);

const exportFormats = computed(() => AVAILABLE_EXPORT_FORMATS);

const exportFormatName = computed(() => {
    const format = exportFormats.value.find((f) => f.id === exportData.modelStoreFormat);
    return format ? format.name : "";
});

const zenodoSource = computed(() => getZenodoSource());

const wizard = useWizard({
    "select-format": {
        label: "Select output format",
        instructions: computed(() => {
            return `Select the format you would like to export the ${resource} to and click Next to continue.`;
        }),
        isValid: () => true,
        isSkippable: () => false,
    },
    "select-destination": {
        label: "Select destination",
        instructions: computed(() => {
            return `Select where you would like to export the ${resource} ${exportFormatName.value} to and click Next to continue.`;
        }),
        isValid: () => true,
        isSkippable: () => false,
    },
    "setup-remote": {
        label: "Select remote source",
        instructions: "Select remote source directory",
        isValid: () => Boolean(exportData.remoteUri),
        isSkippable: () => exportData.destination !== "remote-source",
    },
    "setup-rdm": {
        label: "Select RDM repository",
        instructions: "Select RDM repository and provide a draft record to export to",
        isValid: () => Boolean(exportData.remoteUri),
        isSkippable: () => exportData.destination !== "rdm-repository",
    },
    "setup-zenodo": {
        label: "Select draft record",
        instructions: "Select or create a draft record to export to",
        isValid: () => Boolean(exportData.remoteUri),
        isSkippable: () => exportData.destination !== "zenodo-repository",
    },
    "export-summary": {
        label: "Export",
        instructions: "Summary",
        isValid: () => Boolean(exportData.outputFileName) || exportData.destination === "download",
        isSkippable: () => false,
    },
});

watch(
    () => props.isBusy,
    (newValue, oldValue) => {
        if (oldValue && !newValue) {
            resetWizard();
        }
    }
);

function getZenodoSource() {
    const zenodoSources = getFileSourcesByType("zenodo");
    // Prioritize the one provided by the user in case there are multiple
    return zenodoSources.find((fs) => isPrivateFileSource(fs) && fs.writable) ?? getFileSourceById("zenodo");
}

function onRecordSelected(recordUri: string) {
    exportData.remoteUri = recordUri;
}

async function exportHistory() {
    emit("onExport", exportData);
}

function initializeExportDestinations(): ExportDestinationInfo[] {
    const destinations: ExportDestinationInfo[] = [
        {
            destination: "download",
            label: "Temporary Direct Download",
            markdownDescription: `Generate a link to the export file and download it directly to your computer.

**Please note that the link will expire after 24 hours.**`,
        },
    ];

    if (hasWritableFileSources.value) {
        destinations.push({
            destination: "remote-source",
            label: "Repository",
            markdownDescription: `If you need a **more permanent** way of storing your ${resource} you can export it directly to one of the available repositories. You will be able to re-import it later as long as it remains available on the remote server.

Examples of remote sources include Amazon S3, Azure Storage, Google Drive... and other public or personal file sources that you have setup access to.`,
        });
    }

    if (hasWritableRDMFileSources.value) {
        destinations.push({
            destination: "rdm-repository",
            label: "RDM Repository",
            markdownDescription: `You can upload your ${resource} to one of the available **Research Data Management repositories** here.
This will allow you to easily associate your ${resource} with your research project or publication.

Examples of RDM repositories include [Invenio RDM](https://inveniosoftware.org/products/rdm/) instances, [RSpace](https://www.researchspace.com/), and other public or personal repositories that you have setup access to.`,
        });
    }

    if (zenodoSource.value) {
        destinations.push({
            destination: "zenodo-repository",
            label: `${zenodoSource.value.label}`,
            markdownDescription: `![Zenodo Logo](https://raw.githubusercontent.com/zenodo/zenodo/master/zenodo/modules/theme/static/img/logos/zenodo-gradient-square.svg)

[Zenodo](https://zenodo.org/) is a general-purpose open repository developed under the [European OpenAIRE](https://www.openaire.eu/) program and operated by [CERN](https://home.cern/). It allows researchers to deposit research papers, data sets, research software, reports, and any other research related digital artefacts. For each submission, a persistent **digital object identifier (DOI)** is minted, which makes the stored items easily citeable.`,
        });
    }

    return destinations;
}

function initializeExportData(): HistoryExportData {
    return {
        ...DEFAULT_EXPORT_PARAMS,
        destination: "download",
        remoteUri: "",
        outputFileName: "",
    };
}

function resetWizard() {
    const initialExportData = initializeExportData();
    Object.assign(exportData, initialExportData);
    wizard.goTo("select-format");
}
</script>

<template>
    <div>
        <BAlert v-if="errorMessage" show dismissible fade variant="danger" @dismissed="errorMessage = undefined">
            {{ errorMessage }}
        </BAlert>
        <GenericWizard
            class="history-export-wizard"
            :use="wizard"
            :submit-button-label="exportButtonLabel"
            :is-busy="isBusy"
            @submit="exportHistory">
            <div v-if="wizard.isCurrent('select-format')">
                <BCardGroup deck>
                    <BCard
                        v-for="format in exportFormats"
                        :key="format.id"
                        :data-history-export-format="format.id"
                        class="wizard-selection-card"
                        :border-variant="borderVariant(exportData.modelStoreFormat == format.id)"
                        @click="exportData.modelStoreFormat = format.id">
                        <BCardTitle>
                            <b>{{ format.name }}</b>
                        </BCardTitle>
                        <div v-if="format.id === 'rocrate.zip'">
                            <p>
                                RO-Crate is a community effort to establish a lightweight approach to packaging research
                                data with their metadata. It makes use of schema.org annotations in JSON-LD format.
                            </p>
                            <img
                                class="card-img"
                                src="https://www.researchobject.org/ro-crate/assets/img/ro-crate-wide.svg"
                                alt="RO-Crate Logo" />
                            <br />
                            <ExternalLink href="https://www.researchobject.org/ro-crate/">
                                <b>Learn more</b>
                            </ExternalLink>
                        </div>
                        <div v-else>
                            <p>A compressed tar.gz archive containing the history and its metadata.</p>
                        </div>
                    </BCard>
                </BCardGroup>
            </div>

            <div v-if="wizard.isCurrent('select-destination')">
                <BCardGroup deck>
                    <BCard
                        v-for="target in exportDestinationTargets"
                        :key="target.destination"
                        :data-history-export-destination="target.destination"
                        :border-variant="borderVariant(exportData.destination === target.destination)"
                        :header-bg-variant="exportData.destination === target.destination ? 'primary' : 'default'"
                        :header-text-variant="exportData.destination === target.destination ? 'white' : 'default'"
                        :header="target.label"
                        class="wizard-selection-card"
                        @click="exportData.destination = target.destination">
                        <!-- eslint-disable-next-line vue/no-v-html -->
                        <div v-html="renderMarkdown(target.markdownDescription)" />
                    </BCard>
                </BCardGroup>
            </div>

            <div v-if="wizard.isCurrent('setup-remote')">
                <BFormGroup
                    id="fieldset-directory"
                    label-for="directory"
                    :description="`Select a 'repository' to export ${resource} to.`"
                    class="mt-3">
                    <FilesInput
                        id="directory"
                        v-model="exportData.remoteUri"
                        mode="directory"
                        :require-writable="true"
                        :filter-options="{ exclude: ['rdm'] }" />
                </BFormGroup>
            </div>

            <div v-if="wizard.isCurrent('setup-rdm')">
                <RDMCredentialsInfo what="history export archive" />

                <RDMDestinationSelector :what="resource" @onRecordSelected="onRecordSelected" />
            </div>

            <div v-if="wizard.isCurrent('setup-zenodo')">
                <div class="zenodo-info">
                    <img
                        class="card-img"
                        src="https://raw.githubusercontent.com/zenodo/zenodo/master/zenodo/modules/theme/static/img/logos/zenodo-gradient-square.svg"
                        alt="ZENODO Logo" />

                    <div>
                        <RDMCredentialsInfo
                            what="history export archive"
                            :selected-repository="zenodoSource"
                            :is-private-file-source="zenodoSource ? isPrivateFileSource(zenodoSource) : false" />
                    </div>
                </div>

                <RDMDestinationSelector
                    :what="resource"
                    :file-source="zenodoSource"
                    @onRecordSelected="onRecordSelected" />
            </div>

            <div v-if="wizard.isCurrent('export-summary')">
                <BFormGroup
                    v-if="needsFileName"
                    label-for="exported-file-name"
                    :description="`Give the exported file a name.`"
                    class="mt-3">
                    <BFormInput
                        id="exported-file-name"
                        v-model="exportData.outputFileName"
                        :placeholder="defaultFileName"
                        required />
                </BFormGroup>

                <BFormGroup label="Dataset files included in the package:">
                    <BFormCheckbox v-model="exportData.includeFiles" switch> Include Active Files </BFormCheckbox>

                    <BFormCheckbox v-model="exportData.includeDeleted" switch>
                        Include Deleted (not purged)
                    </BFormCheckbox>

                    <BFormCheckbox v-model="exportData.includeHidden" switch> Include Hidden </BFormCheckbox>
                </BFormGroup>

                <br />

                <div>
                    Format <b>{{ exportFormatName }}</b>
                </div>

                <div>
                    Destination
                    <b>{{ exportDestinationSummary }}</b>
                    <b v-if="exportData.destination !== 'download' && exportData.remoteUri">
                        <FileSourceNameSpan :uri="exportData.remoteUri" class="text-primary" />
                    </b>
                </div>

                <div v-if="needsFileName && exportData.outputFileName">
                    File Name <b>{{ exportData.outputFileName }}.{{ exportData.modelStoreFormat }}</b>
                </div>
            </div>
        </GenericWizard>
    </div>
</template>

<style scoped lang="scss">
.zenodo-info {
    display: flex;
    align-items: flex-start;
    gap: 1rem;
    margin-bottom: 1rem;
}

.wizard-selection-card {
    cursor: pointer;
    transition: border-color 0.15s ease-in-out;

    &:hover {
        border-color: #007bff;
    }
}

.card-img {
    height: auto;
    width: auto;
    max-height: 100px;
    max-width: 100%;
    max-inline-size: -webkit-fill-available;
}
</style>
