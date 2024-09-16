<script setup lang="ts">
import { faCheck, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useStepper } from "@vueuse/core";
import {
    BAlert,
    BCard,
    BCardBody,
    BCardGroup,
    BCardImg,
    BCardTitle,
    BFormCheckbox,
    BFormGroup,
    BFormInput,
} from "bootstrap-vue";
import { computed, reactive, ref } from "vue";

import { GalaxyApi } from "@/api";
import {
    AVAILABLE_INVOCATION_EXPORT_PLUGINS,
    getInvocationExportPluginByType,
    type InvocationExportPluginType,
} from "@/components/Workflow/Invocation/Export/Plugins";
import {
    type BcoDatabaseExportData,
    saveInvocationBCOToDatabase,
} from "@/components/Workflow/Invocation/Export/Plugins/BioComputeObject/service";
import { useFileSources } from "@/composables/fileSources";
import { useMarkdown } from "@/composables/markdown";
import { useShortTermStorageMonitor } from "@/composables/shortTermStorageMonitor";
import { useTaskMonitor } from "@/composables/taskMonitor";
import { errorMessageAsString } from "@/utils/simple-error";

import RDMCredentialsInfo from "@/components/Common/RDMCredentialsInfo.vue";
import RDMDestinationSelector from "@/components/Common/RDMDestinationSelector.vue";
import ExternalLink from "@/components/ExternalLink.vue";
import FilesInput from "@/components/FilesDialog/FilesInput.vue";
import FileSourceNameSpan from "@/components/FileSources/FileSourceNameSpan.vue";
import ExistingInvocationExportProgressCard from "@/components/Workflow/Invocation/Export/ExistingInvocationExportProgressCard.vue";

const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true });

const taskMonitor = useTaskMonitor();
const stsMonitor = useShortTermStorageMonitor();

const { hasWritable: hasWritableFileSources } = useFileSources({ exclude: ["rdm"] });
const { hasWritable: hasWritableRDMFileSources } = useFileSources({ include: ["rdm"] });

const resource = "workflow invocation";

type InvocationExportDestination = "download" | "remote-source" | "rdm-repository" | "bco-database";

interface ExportDestinationInfo {
    destination: InvocationExportDestination;
    label: string;
    markdownDescription: string;
}

interface InvocationExportData {
    exportPluginFormat: InvocationExportPluginType;
    destination: InvocationExportDestination;
    remoteUri: string;
    outputFileName: string;
    includeData: boolean;
    bcoDatabase: BcoDatabaseExportData;
}

interface Props {
    invocationId: string;
}

const props = defineProps<Props>();

const exportToRemoteTaskId = ref();
const exportToStsRequestId = ref();
const errorMessage = ref<string>();

const existingProgress = ref<InstanceType<typeof ExistingInvocationExportProgressCard>>();

const exportData: InvocationExportData = reactive({
    exportPluginFormat: "ro-crate",
    destination: "download",
    remoteUri: "",
    outputFileName: "",
    includeData: true,
    bcoDatabase: {
        serverBaseUrl: "https://biocomputeobject.org",
        table: "GALXY",
        ownerGroup: "",
        authorization: "",
    },
});

const exportButtonLabel = computed(() => {
    switch (exportData.destination) {
        case "download":
            return "Generate Download Link";
        case "remote-source":
            return "Export to Remote Source";
        case "rdm-repository":
            return "Export to RDM Repository";
        case "bco-database":
            return "Export to BCODB";
        default:
            return "Export";
    }
});

const needsFileName = computed(
    () => exportData.destination === "remote-source" || exportData.destination === "rdm-repository"
);

const canIncludeData = computed(() => exportData.exportPluginFormat !== "bco");

const exportDestinationSummary = computed(() => {
    const exportDestination = exportDestinationTargets.value.find(
        (target) => target.destination === exportData.destination
    );
    return exportDestination?.label ?? "Unknown Destination";
});

const exportDestinationTargets = computed(initializeExportDestinations);

const exportPlugins = computed(() => Array.from(AVAILABLE_INVOCATION_EXPORT_PLUGINS.values()));

const selectedExportPlugin = computed(() => getInvocationExportPluginByType(exportData.exportPluginFormat));

const exportDestinationUri = computed(() => {
    const uri = `${exportData.remoteUri}/${exportData.outputFileName}.${selectedExportPlugin.value.exportParams.modelStoreFormat}`;
    return uri;
});

const exportPluginTitle = computed(() => {
    const plugin = getInvocationExportPluginByType(exportData.exportPluginFormat);
    return plugin ? plugin.title : "";
});

const isBusy = ref(false);

const isWizardBusy = computed(() => stsMonitor.isRunning.value || taskMonitor.isRunning.value || isBusy.value);

const stepper = useStepper({
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
            return `Select where you would like to export the ${resource} ${exportPluginTitle.value} to and click Next to continue.`;
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
    "setup-bcodb": {
        label: "Select BCODB Server",
        instructions: "Provide BCODB server and authentication details",
        isValid: () =>
            Boolean(
                exportData.bcoDatabase.serverBaseUrl &&
                    exportData.bcoDatabase.authorization &&
                    exportData.bcoDatabase.table &&
                    exportData.bcoDatabase.ownerGroup
            ),
        isSkippable: () => exportData.destination !== "bco-database",
    },
    "export-summary": {
        label: "Export",
        instructions: "Summary",
        isValid: () =>
            Boolean(exportData.outputFileName) ||
            exportData.destination === "download" ||
            exportData.destination === "bco-database",
        isSkippable: () => false,
    },
});

function goNext() {
    if (stepper.current.value.isValid()) {
        if (stepper.isLast.value) {
            return exportInvocation();
        }

        let nextStepIndex = stepper.index.value + 1;
        let nextStepName = stepper.stepNames.value.at(nextStepIndex);

        while (nextStepName && stepper.steps.value[nextStepName].isSkippable()) {
            nextStepIndex++;
            nextStepName = stepper.stepNames.value.at(nextStepIndex);
        }

        if (nextStepName) {
            stepper.goTo(nextStepName);
        }
    }
}

function goBack() {
    let previousStepIndex = stepper.index.value - 1;
    let previousStepName = stepper.stepNames.value.at(previousStepIndex);

    while (previousStepName && stepper.steps.value[previousStepName].isSkippable()) {
        previousStepIndex--;
        previousStepName = stepper.stepNames.value.at(previousStepIndex);
    }

    if (previousStepName) {
        stepper.goTo(previousStepName);
    }
}

function onRecordSelected(recordUri: string) {
    exportData.remoteUri = recordUri;
}

async function exportInvocation() {
    switch (exportData.destination) {
        case "download":
            await exportToSts();
            break;
        case "remote-source":
        case "rdm-repository":
            await exportToFileSource();
            break;
        case "bco-database":
            isBusy.value = true;
            await saveInvocationBCOToDatabase(props.invocationId, exportData.bcoDatabase);
            isBusy.value = false;
            break;
    }
    //@ts-ignore incorrect property does not exist on type error
    existingProgress.value?.updateExistingExportProgress();
}

async function exportToSts() {
    const { data, error } = await GalaxyApi().POST("/api/invocations/{invocation_id}/prepare_store_download", {
        params: { path: { invocation_id: props.invocationId } },
        body: {
            model_store_format: selectedExportPlugin.value.exportParams.modelStoreFormat,
            include_deleted: selectedExportPlugin.value.exportParams.includeDeleted,
            include_hidden: selectedExportPlugin.value.exportParams.includeHidden,
            include_files: exportData.includeData,
            bco_merge_history_metadata: false,
        },
    });

    if (error) {
        errorMessage.value = errorMessageAsString(error);
        return;
    }

    exportToStsRequestId.value = data.storage_request_id;
}

async function exportToFileSource() {
    const { data, error } = await GalaxyApi().POST("/api/invocations/{invocation_id}/write_store", {
        params: {
            path: { invocation_id: props.invocationId },
        },
        body: {
            target_uri: exportDestinationUri.value,
            model_store_format: selectedExportPlugin.value.exportParams.modelStoreFormat,
            include_deleted: selectedExportPlugin.value.exportParams.includeDeleted,
            include_hidden: selectedExportPlugin.value.exportParams.includeHidden,
            include_files: exportData.includeData,
            bco_merge_history_metadata: false,
        },
    });

    if (error) {
        errorMessage.value = errorMessageAsString(error);
        return;
    }

    exportToRemoteTaskId.value = data.id;
}

function determineDisplayStepIndex(index: number): number {
    const steps = Array.from(Object.values(stepper.steps.value));
    return steps.slice(0, index).filter((step) => !step.isSkippable()).length + 1;
}

function allStepsBeforeAreValid(index: number): boolean {
    const steps = Array.from(Object.values(stepper.steps.value));
    return steps.slice(0, index).every((step) => step.isValid() || step.isSkippable());
}

function isStepDone(currentIndex: number): boolean {
    return currentIndex < stepper.index.value;
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

    if (exportData.exportPluginFormat === "bco") {
        destinations.push({
            destination: "bco-database",
            label: "BCO Database",
            markdownDescription: `You can upload your ${resource} to a **BCODB** server here.

Submission to the BCODB **requires that a user already has an authenticated account** at the server they wish to submit to.
More information about how to set up an account and submit data to a BCODB server can be found [here](https://w3id.org/biocompute/tutorials/galaxy_quick_start).`,
        });
    }

    if (hasWritableFileSources.value) {
        destinations.push({
            destination: "remote-source",
            label: "Remote File Source",
            markdownDescription: `If you need a **more permanent** way of storing your ${resource} you can export it directly to one of the available remote file sources here. You will be able to re-import it later as long as it remains available on the remote server.

Examples of remote sources include Amazon S3, Azure Storage, Google Drive... and other public or personal file sources that you have setup access to.`,
        });
    }

    if (hasWritableRDMFileSources.value) {
        destinations.push({
            destination: "rdm-repository",
            label: "RDM Repository",
            markdownDescription: `You can upload your ${resource} to one of the available **Research Data Management repositories** here.
This will allow you to easily associate your ${resource} with your research project or publication.

Examples of RDM repositories include [Zenodo](https://zenodo.org/), [Invenio RDM](https://inveniosoftware.org/products/rdm/) instances, and other public or personal repositories that you have setup access to.`,
        });
    }

    return destinations;
}

/**
 * This is a workaround to make the grid columns template dynamic based on the number of visible steps.
 */
const stepsGridColumnsTemplate = computed(() => {
    const numVisibleSteps = Array.from(Object.values(stepper.steps.value)).filter((step) => !step.isSkippable()).length;
    return (
        Array(numVisibleSteps - 1)
            .fill("auto")
            .join(" ") + " max-content"
    );
});
</script>

<template>
    <div>
        <ExistingInvocationExportProgressCard
            ref="existingProgress"
            :invocation-id="invocationId"
            :export-to-remote-task-id="exportToRemoteTaskId"
            :export-to-remote-target-uri="exportData.remoteUri"
            :export-to-sts-request-id="exportToStsRequestId"
            :use-sts-monitor="stsMonitor"
            :use-remote-monitor="taskMonitor"
            @onDismissSts="exportToStsRequestId = undefined"
            @onDismissRemote="exportToRemoteTaskId = undefined" />
        <BCard class="invocation-export-wizard">
            <BCardTitle>
                <h2>Export Workflow Invocation Wizard</h2>
            </BCardTitle>
            <BCardBody class="wizard">
                <BCard>
                    <BCardBody class="wizard-steps">
                        <div
                            v-for="(step, id, i) in stepper.steps.value"
                            :key="id"
                            class="wizard-step"
                            :class="step.isSkippable() ? 'skipped ' : ''">
                            <button
                                class="step-number"
                                :class="{ active: stepper.isCurrent(id), done: isStepDone(i) }"
                                :disabled="(!allStepsBeforeAreValid(i) && stepper.isBefore(id)) || isWizardBusy"
                                @click="stepper.goTo(id)">
                                <FontAwesomeIcon v-if="isStepDone(i)" :icon="faCheck" />
                                <FontAwesomeIcon v-else-if="stepper.isLast && isWizardBusy" :icon="faSpinner" spin />
                                <span v-else>{{ determineDisplayStepIndex(i) }}</span>
                            </button>
                            <div class="step-label" v-text="step.label" />
                            <div class="step-line" :class="{ fill: stepper.isAfter(id) }"></div>
                        </div>
                    </BCardBody>
                </BCard>

                <div class="step-content">
                    <span class="h-md step-instructions" v-text="stepper.current.value.instructions" />

                    <div class="step-body">
                        <div v-if="stepper.isCurrent('select-format')">
                            <BCardGroup deck>
                                <BCard
                                    v-for="plugin in exportPlugins"
                                    :key="plugin.id"
                                    class="wizard-selection-card"
                                    :border-variant="
                                        exportData.exportPluginFormat === plugin.id ? 'primary' : 'default'
                                    "
                                    @click="exportData.exportPluginFormat = plugin.id">
                                    <BCardTitle>
                                        <b>{{ plugin.title }}</b>
                                    </BCardTitle>
                                    <div v-if="plugin.img">
                                        <BCardImg :src="plugin.img" :alt="plugin.title" />
                                        <br />
                                        <ExternalLink v-if="plugin.url" :href="plugin.url">
                                            <b>Learn more</b>
                                        </ExternalLink>
                                    </div>
                                    <div v-else v-html="renderMarkdown(plugin.markdownDescription)" />
                                </BCard>
                            </BCardGroup>
                        </div>

                        <div v-if="stepper.isCurrent('select-destination')">
                            <BCardGroup deck>
                                <BCard
                                    v-for="target in exportDestinationTargets"
                                    :key="target.destination"
                                    :border-variant="
                                        exportData.destination === target.destination ? 'primary' : 'default'
                                    "
                                    :header-bg-variant="
                                        exportData.destination === target.destination ? 'primary' : 'default'
                                    "
                                    :header-text-variant="
                                        exportData.destination === target.destination ? 'white' : 'default'
                                    "
                                    :header="target.label"
                                    class="wizard-selection-card"
                                    @click="exportData.destination = target.destination">
                                    <div v-html="renderMarkdown(target.markdownDescription)" />
                                </BCard>
                            </BCardGroup>
                        </div>

                        <div v-if="stepper.isCurrent('setup-remote')">
                            <BFormGroup
                                id="fieldset-directory"
                                label-for="directory"
                                :description="`Select a 'remote files' directory to export ${resource} to.`"
                                class="mt-3">
                                <FilesInput
                                    id="directory"
                                    v-model="exportData.remoteUri"
                                    mode="directory"
                                    :require-writable="true"
                                    :filter-options="{ exclude: ['rdm'] }" />
                            </BFormGroup>
                        </div>

                        <div v-if="stepper.isCurrent('setup-rdm')">
                            <RDMCredentialsInfo />

                            <RDMDestinationSelector :what="resource" @onRecordSelected="onRecordSelected" />
                        </div>

                        <div v-if="stepper.isCurrent('setup-bcodb')">
                            <p>
                                To submit to a BCODB you need to already have an authenticated account. Instructions on
                                submitting a BCO from Galaxy are available
                                <ExternalLink
                                    href="https://w3id.org/biocompute/tutorials/galaxy_quick_start/"
                                    target="_blank">
                                    here
                                </ExternalLink>
                            </p>
                            <BFormGroup
                                label-for="bcodb-server"
                                description="BCO DB URL (example: https://biocomputeobject.org)">
                                <BFormInput
                                    id="bcodb-server"
                                    v-model="exportData.bcoDatabase.serverBaseUrl"
                                    type="text"
                                    placeholder="https://biocomputeobject.org"
                                    autocomplete="off"
                                    required />
                            </BFormGroup>

                            <BFormGroup label-for="bcodb-table" description="Prefix">
                                <BFormInput
                                    id="bcodb-table"
                                    v-model="exportData.bcoDatabase.table"
                                    type="text"
                                    placeholder="GALXY"
                                    autocomplete="off"
                                    required />
                            </BFormGroup>

                            <BFormGroup label-for="bcodb-owner" description="User Name">
                                <BFormInput
                                    id="bcodb-owner"
                                    v-model="exportData.bcoDatabase.ownerGroup"
                                    type="text"
                                    autocomplete="off"
                                    required />
                            </BFormGroup>

                            <BFormGroup label-for="bcodb-authorization" description="User API Key">
                                <BFormInput
                                    id="bcodb-authorization"
                                    v-model="exportData.bcoDatabase.authorization"
                                    type="password"
                                    autocomplete="off"
                                    required />
                            </BFormGroup>
                        </div>

                        <div v-if="stepper.isCurrent('export-summary')">
                            <BFormGroup
                                v-if="needsFileName"
                                label-for="exported-file-name"
                                :description="`Give the exported file a name.`"
                                class="mt-3">
                                <BFormInput
                                    id="exported-file-name"
                                    v-model="exportData.outputFileName"
                                    placeholder="enter file name"
                                    required />
                            </BFormGroup>

                            <BFormCheckbox
                                v-if="canIncludeData"
                                id="include-data"
                                v-model="exportData.includeData"
                                switch>
                                Include data files in the export package.
                            </BFormCheckbox>

                            <br />

                            <div>
                                Format <b>{{ exportPluginTitle }}</b>
                            </div>

                            <div>
                                Destination
                                <b>{{ exportDestinationSummary }}</b>
                                <b v-if="exportData.destination !== 'download' && exportData.remoteUri">
                                    <FileSourceNameSpan :uri="exportData.remoteUri" class="text-primary" />
                                </b>
                                <b v-if="exportData.destination === 'bco-database'">
                                    <span class="text-primary">{{ exportData.bcoDatabase.table }}</span>
                                    <ExternalLink :href="exportData.bcoDatabase.serverBaseUrl">
                                        {{ exportData.bcoDatabase.serverBaseUrl }}
                                    </ExternalLink>
                                </b>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="wizard-actions">
                    <button v-if="!stepper.isFirst.value" class="go-back-btn" :disabled="isWizardBusy" @click="goBack">
                        Back
                    </button>

                    <button
                        class="go-next-btn"
                        :disabled="!stepper.current.value.isValid() || isWizardBusy"
                        :class="stepper.isLast.value ? 'btn-primary' : ''"
                        @click="goNext">
                        {{ stepper.isLast.value ? exportButtonLabel : "Next" }}
                    </button>
                </div>
            </BCardBody>
        </BCard>
        <BAlert v-if="errorMessage" show dismissible fade variant="danger" @dismissed="errorMessage = undefined">
            {{ errorMessage }}
        </BAlert>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.wizard {
    padding: 0;

    .wizard-steps {
        padding: 0;
        margin: 0;
        display: grid;
        grid-auto-flow: column;
        grid-template-columns: v-bind(stepsGridColumnsTemplate);
    }

    .wizard-step {
        padding: 0;
        margin: 0;
        display: grid;
        grid-template-columns: 50px max-content auto;
        grid-template-rows: auto;
        grid-template-areas: "number label line";
        justify-items: center;

        .step-number {
            border-radius: 50%;
            width: 40px;
            height: 40px;
            background-color: $brand-secondary;
            justify-content: center;
            align-items: center;
            font-size: 1rem;
            grid-area: number;

            &.active {
                background-color: $brand-primary;
                color: white;
            }

            &.done {
                background-color: $brand-success;
                color: white;
            }
        }

        .step-label {
            align-self: center;
            grid-area: label;
            text-align: center;
            text-wrap: nowrap;
        }

        .step-line {
            margin-left: 5px;
            align-self: center;
            grid-area: line;
            width: 0;
            height: 4px;
            background-color: $brand-primary;

            &.fill {
                width: 100%;
                transform-origin: left;
                transition: width 0.2s;
            }
        }

        &.skipped {
            display: none;
        }

        &:last-child {
            justify-self: end;
        }
    }

    .step-content {
        padding: 1rem 1rem 0rem 1rem;
        display: flex;
        flex-direction: column;
        align-items: center;

        .step-instructions {
            margin-top: 0rem;
            margin-bottom: 1rem;
        }

        .step-body {
            display: flex;
            flex-direction: column;
            align-items: center;
        }
    }

    .wizard-actions {
        padding: 1rem 1rem 0rem 1rem;

        .go-back-btn {
            float: left;
        }

        .go-next-btn {
            float: right;
        }
    }

    .wizard-selection-card {
        border-width: 3px;
        text-align: center;

        .card-header {
            border-radius: 0;
        }
    }
}

.card-img {
    height: auto;
    width: auto;
    max-height: 100px;
    max-inline-size: -webkit-fill-available;
}
</style>
