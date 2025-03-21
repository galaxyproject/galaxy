<script setup lang="ts">
import { BAlert, BCard, BCardGroup, BCardImg, BCardTitle, BFormCheckbox, BFormGroup, BFormInput } from "bootstrap-vue";
import { computed, reactive, ref, watch } from "vue";

import { GalaxyApi } from "@/api";
import { useWizard } from "@/components/Common/Wizard/useWizard";
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
import GenericWizard from "@/components/Common/Wizard/GenericWizard.vue";
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

const exportData: InvocationExportData = reactive(initializeExportData());

const exportButtonLabel = computed(() => {
    switch (exportData.destination) {
        case "download":
            return "生成下载链接";
        case "remote-source":
            return "导出到远程源";
        case "rdm-repository":
            return "导出到RDM仓库";
        case "bco-database":
            return "导出到BCODB";
        default:
            return "导出";
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
    return exportDestination?.label ?? "未知目的地";
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

const wizard = useWizard({
    "select-format": {
        label: "选择输出格式",
        instructions: computed(() => {
            return `选择您想要导出的${resource}格式，然后点击下一步继续。`;
        }),
        isValid: () => true,
        isSkippable: () => false,
    },
    "select-destination": {
        label: "选择目的地",
        instructions: computed(() => {
            return `选择您想要导出的${resource}${exportPluginTitle.value}的目的地，然后点击下一步继续。`;
        }),
        isValid: () => true,
        isSkippable: () => false,
    },
    "setup-remote": {
        label: "选择远程源",
        instructions: "选择远程源目录",
        isValid: () => Boolean(exportData.remoteUri),
        isSkippable: () => exportData.destination !== "remote-source",
    },
    "setup-rdm": {
        label: "选择RDM仓库",
        instructions: "选择RDM仓库并提供要导出的草稿记录",
        isValid: () => Boolean(exportData.remoteUri),
        isSkippable: () => exportData.destination !== "rdm-repository",
    },
    "setup-bcodb": {
        label: "选择BCODB服务器",
        instructions: "提供BCODB服务器和认证详情",
        isValid: () =>
            Boolean(
                exportData.bcoDatabase.serverBaseUrl &&
                    exportData.bcoDatabase.authorization &&
                    exportData.bcoDatabase.table &&
                    exportData.bcoDatabase.ownerGroup
            ),
        isSkippable: () => exportData.destination !== "bco-database" || exportData.exportPluginFormat !== "bco",
    },
    "export-summary": {
        label: "导出",
        instructions: "摘要",
        isValid: () =>
            Boolean(exportData.outputFileName) ||
            exportData.destination === "download" ||
            exportData.destination === "bco-database",
        isSkippable: () => false,
    },
});

watch(
    () => exportData.exportPluginFormat,
    () => {
        // Only allow BCO format to be exported to BCODB
        if (exportData.destination === "bco-database" && exportData.exportPluginFormat !== "bco") {
            exportData.destination = "download";
        }
    }
);

watch(
    () => isWizardBusy.value,
    (newValue, oldValue) => {
        if (oldValue && !newValue) {
            resetWizard();
        }
    }
);

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

function initializeExportDestinations(): ExportDestinationInfo[] {
    const destinations: ExportDestinationInfo[] = [
        {
            destination: "download",
            label: "临时直接下载",
            markdownDescription: `生成导出文件的链接并直接下载到您的计算机。

**请注意，链接将在24小时后过期。**`,
        },
    ];

    if (exportData.exportPluginFormat === "bco") {
        destinations.push({
            destination: "bco-database",
            label: "BCO数据库",
            markdownDescription: `您可以在此处将${resource}上传到**BCODB**服务器。

提交到BCODB**需要用户在他们希望提交的服务器上已经拥有经过认证的账户**。
关于如何设置账户并向BCODB服务器提交数据的更多信息可以在[这里](https://w3id.org/biocompute/tutorials/galaxy_quick_start)找到。`,
        });
    }

    if (hasWritableFileSources.value) {
        destinations.push({
            destination: "remote-source",
            label: "远程文件源",
            markdownDescription: `如果您需要**更永久**的方式来存储${resource}，您可以直接将其导出到可用的远程文件源之一。只要它在远程服务器上仍然可用，您以后就可以重新导入它。

远程源的例子包括亚马逊S3、Azure存储、谷歌云端硬盘...以及您已经设置访问权限的其他公共或个人文件源。`,
        });
    }

    if (hasWritableRDMFileSources.value) {
        destinations.push({
            destination: "rdm-repository",
            label: "RDM仓库",
            markdownDescription: `您可以在此处将${resource}上传到可用的**研究数据管理仓库**之一。
这将使您能够轻松地将${resource}与您的研究项目或出版物相关联。

RDM仓库的例子包括[Zenodo](https://zenodo.org/)、[Invenio RDM](https://inveniosoftware.org/products/rdm/)实例，以及您已经设置访问权限的其他公共或个人仓库。`,
        });
    }

    return destinations;
}

function initializeExportData(): InvocationExportData {
    return {
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
        <GenericWizard
            class="invocation-export-wizard"
            title="调用导出向导"
            :use="wizard"
            :submit-button-label="exportButtonLabel"
            :is-busy="isWizardBusy"
            @submit="exportInvocation">
            <div v-if="wizard.isCurrent('select-format')">
                <BCardGroup deck>
                    <BCard
                        v-for="plugin in exportPlugins"
                        :key="plugin.id"
                        :data-invocation-export-type="plugin.id"
                        class="wizard-selection-card"
                        :border-variant="exportData.exportPluginFormat === plugin.id ? 'primary' : 'default'"
                        @click="exportData.exportPluginFormat = plugin.id">
                        <BCardTitle>
                            <b>{{ plugin.title }}</b>
                        </BCardTitle>
                        <div v-if="plugin.img">
                            <BCardImg :src="plugin.img" :alt="plugin.title" />
                            <br />
                            <ExternalLink v-if="plugin.url" :href="plugin.url">
                                <b>了解更多</b>
                            </ExternalLink>
                        </div>
                        <div v-else v-html="renderMarkdown(plugin.markdownDescription)" />
                    </BCard>
                </BCardGroup>
            </div>

            <div v-if="wizard.isCurrent('select-destination')">
                <BCardGroup deck>
                    <BCard
                        v-for="target in exportDestinationTargets"
                        :key="target.destination"
                        :data-invocation-export-destination="target.destination"
                        :border-variant="exportData.destination === target.destination ? 'primary' : 'default'"
                        :header-bg-variant="exportData.destination === target.destination ? 'primary' : 'default'"
                        :header-text-variant="exportData.destination === target.destination ? 'white' : 'default'"
                        :header="target.label"
                        class="wizard-selection-card"
                        @click="exportData.destination = target.destination">
                        <div v-html="renderMarkdown(target.markdownDescription)" />
                    </BCard>
                </BCardGroup>
            </div>

            <div v-if="wizard.isCurrent('setup-remote')">
                <BFormGroup
                    id="fieldset-directory"
                    label-for="directory"
                    :description="`选择一个'远程文件'目录以导出${resource}。`"
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
                <RDMCredentialsInfo />

                <RDMDestinationSelector :what="resource" @onRecordSelected="onRecordSelected" />
            </div>

            <div v-if="wizard.isCurrent('setup-bcodb')">
                <p>
                    要提交到BCODB，您需要已经有一个认证账户。关于从Galaxy提交BCO的说明，请参见
                    <ExternalLink href="https://w3id.org/biocompute/tutorials/galaxy_quick_start/" target="_blank">
                        这里
                    </ExternalLink>
                </p>
                <BFormGroup label-for="bcodb-server" description="BCO DB URL（例如：https://biocomputeobject.org）">
                    <BFormInput
                        id="bcodb-server"
                        v-model="exportData.bcoDatabase.serverBaseUrl"
                        type="text"
                        placeholder="https://biocomputeobject.org"
                        autocomplete="off"
                        required />
                </BFormGroup>

                <BFormGroup label-for="bcodb-table" description="前缀">
                    <BFormInput
                        id="bcodb-table"
                        v-model="exportData.bcoDatabase.table"
                        type="text"
                        placeholder="GALXY"
                        autocomplete="off"
                        required />
                </BFormGroup>

                <BFormGroup label-for="bcodb-owner" description="用户名">
                    <BFormInput
                        id="bcodb-owner"
                        v-model="exportData.bcoDatabase.ownerGroup"
                        type="text"
                        autocomplete="off"
                        required />
                </BFormGroup>

                <BFormGroup label-for="bcodb-authorization" description="用户API密钥">
                    <BFormInput
                        id="bcodb-authorization"
                        v-model="exportData.bcoDatabase.authorization"
                        type="password"
                        autocomplete="off"
                        required />
                </BFormGroup>
            </div>

            <div v-if="wizard.isCurrent('export-summary')">
                <BFormGroup
                    v-if="needsFileName"
                    label-for="exported-file-name"
                    :description="`给导出的文件命名。`"
                    class="mt-3">
                    <BFormInput
                        id="exported-file-name"
                        v-model="exportData.outputFileName"
                        placeholder="输入文件名"
                        required />
                </BFormGroup>

                <BFormCheckbox v-if="canIncludeData" id="include-data" v-model="exportData.includeData" switch>
                    在导出包中包含数据文件。
                </BFormCheckbox>

                <br />

                <div>
                    格式 <b>{{ exportPluginTitle }}</b>
                </div>

                <div>
                    目的地
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
        </GenericWizard>
        <BAlert v-if="errorMessage" show dismissible fade variant="danger" @dismissed="errorMessage = undefined">
            {{ errorMessage }}
        </BAlert>
    </div>
</template>

<style scoped lang="scss">
.card-img {
    height: auto;
    width: auto;
    max-height: 100px;
    max-inline-size: -webkit-fill-available;
}
</style>
