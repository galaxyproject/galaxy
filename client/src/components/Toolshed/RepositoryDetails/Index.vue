<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";

import { useConfig } from "@/composables/config";
import { useResourceWatcher } from "@/composables/resourceWatcher";
import { useToolStore } from "@/stores/toolStore";
import { errorMessageAsString } from "@/utils/simple-error";

import { Services } from "../services";

import InstallationActions from "./InstallationActions.vue";
import InstallationSettings from "./InstallationSettings.vue";
import RepositoryTools from "./RepositoryTools.vue";

const props = defineProps({
    repo: {
        type: Object,
        required: true,
    },
    toolshedUrl: {
        type: String,
        required: true,
    },
});

const services = new Services();

const { config } = useConfig(true);
const { toolSections, fetchToolSections } = useToolStore();

const repositoryWatcher = useResourceWatcher(loadInstalledRepositories, {
    shortPollingInterval: 2000,
    enableBackgroundPolling: false,
});

const repoChecked = "fa fa-check text-success";
const repoUnchecked = "fa fa-times text-danger";
const repoFields = [
    { key: "numeric_revision", label: "版本" },
    { key: "tools", label: "工具和版本" },
    { key: "profile", label: "依赖" },
    { key: "missing_test_components", label: "测试" },
    { key: "status", label: "状态" },
    { key: "actions", label: "", class: "toolshed-repo-actions" },
];

const statusError = "错误";
const statusInstalled = "已安装";
const statusUninstalled = "已卸载";

const revisionStateMap = new Map();
const revisionWaitStateMap = new Map();

const selectedChangeset = ref();
const selectedRequiresPanel = ref(false);
const repoTable = ref([]);
const showSettings = ref(false);
const error = ref();
const loading = ref(true);

const isActionBusy = computed(() => (item) => {
    return revisionWaitStateMap.has(item.changeset_revision);
});

onMounted(() => {
    load();
    fetchToolSections("default");
    startWatchingRepository();
});

onUnmounted(() => {
    stopWatchingRepository();
});

async function load() {
    try {
        const response = await services.getRepository(props.toolshedUrl, props.repo.id);
        repoTable.value = response ?? [];
        loadInstalledRepositories();
    } catch (e) {
        error.value = errorMessageAsString(e);
        loading.value = false;
    }
}

async function loadInstalledRepositories() {
    try {
        const revisions = await services.getInstalledRepositoriesByName(props.repo.name, props.repo.owner);

        refreshRepositoryStatus(revisions);
    } catch (e) {
        error.value = errorMessageAsString(e);
    } finally {
        loading.value = false;
    }
}

function refreshRepositoryStatus(updatedRevisions) {
    repoTable.value.forEach((x) => {
        const repoRevision = updatedRevisions[x.changeset_revision];
        if (!repoRevision) {
            return;
        }
        revisionStateMap.set(x.changeset_revision, repoRevision);
        if (repoRevision.status !== x.status) {
            x.status = repoRevision.status;
            x.installed = repoRevision.installed;
        }

        if (hasReachedExpectedState(x.changeset_revision) || !isFinalState(repoRevision.status)) {
            // We don't need to particularly watch this revision anymore
            removeRevisionFromWatchList(x.changeset_revision);
        }
    });

    repoTable.value = [...repoTable.value];
}

function isFinalState(status) {
    return [statusError, statusInstalled, statusUninstalled].includes(status);
}

function removeRevisionFromWatchList(changesetRevision) {
    if (revisionWaitStateMap.has(changesetRevision)) {
        revisionWaitStateMap.delete(changesetRevision);
    }
}

function hasReachedExpectedState(changesetRevision) {
    const revisionState = revisionStateMap.get(changesetRevision);
    if (!revisionState) {
        return false;
    }
    const revisionWaitState = revisionWaitStateMap.get(changesetRevision);
    if (!revisionWaitState) {
        // No expected state set, consider it done
        return true;
    }
    const hasReachedExpectedState = revisionWaitState.waitForStates.includes(revisionState.status);
    return hasReachedExpectedState;
}

function onHide() {
    showSettings.value = false;
}

function setupRepository(details) {
    selectedChangeset.value = details.changeset_revision;
    selectedRequiresPanel.value =
        details.includes_tools_for_display_in_tool_panel || details.repository.type === "repository_suite_definition";
    showSettings.value = true;
}

async function onInstallRepository(details) {
    try {
        waitForRevisionStatus({
            changesetRevision: details.changeset_revision,
            waitForStates: [statusInstalled, statusError],
        });
        await services.installRepository(details);
        showSettings.value = false;
    } catch (e) {
        error.value = errorMessageAsString(e);
    }
}

async function uninstallRepository(details) {
    try {
        waitForRevisionStatus({
            changesetRevision: details.changeset_revision,
            waitForStates: [statusUninstalled, statusError],
        });
        await services.uninstallRepository({
            tool_shed_url: props.toolshedUrl,
            name: props.repo.name,
            owner: props.repo.owner,
            changeset_revision: details.changeset_revision,
        });
    } catch (e) {
        error.value = errorMessageAsString(e);
    }
}

async function resetRepository(details) {
    try {
        waitForRevisionStatus({
            changesetRevision: details.changeset_revision,
            waitForStates: [statusUninstalled],
        });
        await services.uninstallRepository({
            tool_shed_url: props.toolshedUrl,
            name: props.repo.name,
            owner: props.repo.owner,
            changeset_revision: details.changeset_revision,
        });
    } catch (e) {
        error.value = errorMessageAsString(e);
    }
}

function waitForRevisionStatus({ changesetRevision, waitForStates }) {
    revisionWaitStateMap.set(changesetRevision, { waitForStates });
    repoTable.value = [...repoTable.value];
}

function startWatchingRepository() {
    repositoryWatcher.startWatchingResource();
}

function stopWatchingRepository() {
    repositoryWatcher.stopWatchingResource();
    revisionStateMap.clear();
    revisionWaitStateMap.clear();
}
</script>

<template>
    <b-card>
        <div class="mb-1">{{ repo.long_description }}</div>
        <div class="mb-3">
            <b-link :href="repo.repository_url" target="_blank">显示更多详情和依赖项。</b-link>
        </div>
        <div>
            <span v-if="loading">
                <span class="fa fa-spinner fa-spin" />
                <span class="loading-message">正在加载仓库详情...</span>
            </span>
            <div v-else>
                <b-alert v-if="error" variant="danger" show>
                    {{ error }}
                </b-alert>
                <div v-else class="border rounded">
                    <b-table borderless :items="repoTable" :fields="repoFields" class="text-center m-0">
                        <template v-slot:cell(numeric_revision)="data">
                            <span class="font-weight-bold">{{ data.value }}</span>
                        </template>
                        <template v-slot:cell(tools)="data">
                            <RepositoryTools :tools="data.value" />
                        </template>
                        <template v-slot:cell(profile)="data">
                            {{ data.value ? `+${data.value}` : "-" }}
                        </template>
                        <template v-slot:cell(missing_test_components)="data">
                            <span v-if="!data.value" :class="repoChecked" />
                            <span v-else :class="repoUnchecked" />
                        </template>
                        <template v-slot:cell(status)="row">
                            <span v-if="row.item.status">
                                <span v-if="!isFinalState(row.item.status)" class="fa fa-spinner fa-spin" />
                                {{ row.item.status }}
                            </span>
                            <span v-else> - </span>
                        </template>
                        <template v-slot:cell(actions)="row">
                            <InstallationActions
                                :status="row.item.status"
                                :is-busy="isActionBusy(row.item)"
                                @onInstall="setupRepository(row.item)"
                                @onUninstall="uninstallRepository(row.item)"
                                @onReset="resetRepository(row.item)" />
                        </template>
                    </b-table>
                    <InstallationSettings
                        v-if="showSettings && selectedChangeset"
                        :repo="repo"
                        :toolshed-url="toolshedUrl"
                        :changeset-revision="selectedChangeset"
                        :requires-panel="selectedRequiresPanel"
                        :current-panel="toolSections['default']"
                        :tool-dynamic-configs="config.tool_dynamic_configs"
                        @hide="onHide"
                        @ok="onInstallRepository" />
                </div>
            </div>
        </div>
    </b-card>
</template>

<style lang="scss">
// make actions take up less space
.toolshed-repo-actions {
    width: 10%;
    min-width: 120px;
}
</style>
