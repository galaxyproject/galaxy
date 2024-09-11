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
import { useFileSources } from "@/composables/fileSources";
import { useMarkdown } from "@/composables/markdown";
import { useShortTermStorageMonitor } from "@/composables/shortTermStorageMonitor";
import { useTaskMonitor } from "@/composables/taskMonitor";
import { errorMessageAsString } from "@/utils/simple-error";

import RDMCredentialsInfo from "@/components/Common/RDMCredentialsInfo.vue";
import RDMDestinationSelector from "@/components/Common/RDMDestinationSelector.vue";
import FilesInput from "@/components/FilesDialog/FilesInput.vue";
import ExistingInvocationExportProgressCard from "@/components/Workflow/Invocation/Export/ExistingInvocationExportProgressCard.vue";

const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true });

const taskMonitor = useTaskMonitor();
const stsMonitor = useShortTermStorageMonitor();

const { hasWritable: hasWritableFileSources } = useFileSources({ exclude: ["rdm"] });
const { hasWritable: hasWritableRDMFileSources } = useFileSources({ include: ["rdm"] });

const resource = "workflow invocation";

type ExportDestination = "download" | "remote-source" | "rdm-repository";

interface ExportDestinationInfo {
    destination: ExportDestination;
    label: string;
    markdownDescription: string;
}

interface ExportData {
    exportPluginFormat: InvocationExportPluginType;
    destination: ExportDestination;
    remoteUri: string;
    outputFileName: string;
    includeData: boolean;
}

interface Props {
    invocationId: string;
}

const props = defineProps<Props>();

const exportToRemoteTaskId = ref();
const exportToStsRequestId = ref();
const errorMessage = ref<string>();

const exportData: ExportData = reactive({
    exportPluginFormat: "ro-crate",
    destination: "download",
    remoteUri: "",
    outputFileName: "",
    includeData: true,
});

const exportButtonLabel = computed(() => {
    switch (exportData.destination) {
        case "download":
            return "Generate Download Link";
        case "remote-source":
            return "Export to Remote Source";
        case "rdm-repository":
            return "Export to RDM Repository";
        default:
            return "Export";
    }
});

const exportDestinationTargets = computed(initializeExportDestinations);

const exportPlugins = computed(() => Array.from(AVAILABLE_INVOCATION_EXPORT_PLUGINS.values()));

const exportPluginTitle = computed(() => {
    const plugin = getInvocationExportPluginByType(exportData.exportPluginFormat);
    return plugin ? plugin.title : "";
});

const isExportRunning = computed(() => stsMonitor.isRunning.value || taskMonitor.isRunning.value);

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
    "export-summary": {
        label: "Export",
        instructions: "Summary",
        isValid: () => Boolean(exportData.outputFileName) || exportData.destination === "download",
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
    if (exportData.destination === "download") {
        await exportToSts();
    } else {
        await exportToFileSource();
    }
    //@ts-ignore incorrect property does not exist on type error
    existingProgress.value?.updateExistingExportProgress();
}

async function exportToSts() {
    const exportPlugin = getInvocationExportPluginByType(exportData.exportPluginFormat);

    const { data, error } = await GalaxyApi().POST("/api/invocations/{invocation_id}/prepare_store_download", {
        params: { path: { invocation_id: props.invocationId } },
        body: {
            model_store_format: exportPlugin.exportParams.modelStoreFormat,
            include_deleted: exportPlugin.exportParams.includeDeleted,
            include_hidden: exportPlugin.exportParams.includeHidden,
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
    const exportPlugin = getInvocationExportPluginByType(exportData.exportPluginFormat);
    const exportDirectoryUri = `${exportData.remoteUri}/${exportData.outputFileName}.${exportPlugin.exportParams.modelStoreFormat}`;

    const { data, error } = await GalaxyApi().POST("/api/invocations/{invocation_id}/write_store", {
        params: {
            path: { invocation_id: props.invocationId },
        },
        body: {
            target_uri: exportDirectoryUri,
            model_store_format: exportPlugin.exportParams.modelStoreFormat,
            include_deleted: exportPlugin.exportParams.includeDeleted,
            include_hidden: exportPlugin.exportParams.includeHidden,
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

    //TODO: Add BCO-database as a destination if BCO selected as export format

    return destinations;
}

const existingProgress = ref<InstanceType<typeof ExistingInvocationExportProgressCard>>();

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
                                :disabled="!allStepsBeforeAreValid(i) && stepper.isBefore(id)"
                                @click="stepper.goTo(id)">
                                <FontAwesomeIcon v-if="isStepDone(i)" :icon="faCheck" />
                                <FontAwesomeIcon v-else-if="stepper.isLast && isExportRunning" :icon="faSpinner" spin />
                                <span v-else>{{ determineDisplayStepIndex(i) }}</span>
                            </button>
                            <div class="step-label" v-text="step.label" />
                            <div class="step-line" :class="{ fill: stepper.isAfter(id) }"></div>
                            <!-- <hr v-if="stepper.isAfter(id)" class="step-line" /> -->
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
                                    <BCardImg v-if="plugin.img" :src="plugin.img" :alt="plugin.title" />
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

                        <div v-if="stepper.isCurrent('export-summary')">
                            <div>
                                <p>Export Format: {{ exportPluginTitle }}</p>
                                <p>Export Destination: {{ exportData.destination }}</p>
                                <BFormGroup
                                    v-if="exportData.destination !== 'download'"
                                    id="fieldset-name"
                                    label-for="name"
                                    :description="`Give the exported file a name.`"
                                    class="mt-3">
                                    <BFormInput
                                        id="name"
                                        v-model="exportData.outputFileName"
                                        placeholder="enter file name"
                                        required />
                                </BFormGroup>

                                <BFormCheckbox id="include-data" v-model="exportData.includeData" switch>
                                    Include data files in the export package.
                                </BFormCheckbox>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="wizard-actions">
                    <button v-if="!stepper.isFirst.value" class="go-back-btn" @click="goBack">Back</button>
                    <button
                        class="go-next-btn"
                        :disabled="!stepper.current.value.isValid() || isExportRunning"
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
