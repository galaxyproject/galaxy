<script setup>
import { onMounted, onUnmounted, ref } from "vue";

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
const { panel, fetchPanel } = useToolStore();

const repositoryWatcher = useResourceWatcher(loadInstalledRepositories, {
    shortPollingInterval: 2000,
    enableBackgroundPolling: false,
});

const repoChecked = "fa fa-check text-success";
const repoUnchecked = "fa fa-times text-danger";
const repoFields = [
    { key: "numeric_revision", label: "Revision" },
    { key: "tools", label: "Tools and Versions" },
    { key: "profile", label: "Requires" },
    { key: "missing_test_components", label: "Tests" },
    { key: "status" },
    { key: "actions", label: "", class: "toolshed-repo-actions" },
];

const selectedChangeset = ref();
const selectedRequiresPanel = ref(false);
const repoTable = ref([]);
const showSettings = ref(false);
const error = ref();
const loading = ref(true);

onMounted(() => {
    load();
    if (!panel["default"]) {
        fetchPanel("default");
    }
});

onUnmounted(() => {
    stopWatchingResource();
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
        let changed = false;
        repoTable.value.forEach((x) => {
            const revision = revisions[x.changeset_revision];
            if (revision && revision.status !== x.status) {
                x.status = revision.status;
                x.installed = revision.installed;
                changed = true;
                return;
            }
        });
        if (changed) {
            repoTable.value = [...repoTable.value];
        }
    } catch (e) {
        error.value = errorMessageAsString(e);
    } finally {
        loading.value = false;
    }
}

function isFinalState(status) {
    return ["Error", "Installed", "Uninstalled"].includes(status);
}

async function onInstallRepository(details) {
    try {
        await services.installRepository(details);
        showSettings.value = false;
        startWatchingResource();
    } catch (e) {
        error.value = errorMessageAsString(e);
    }
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

async function uninstallRepository(details) {
    try {
        await services.uninstallRepository({
            tool_shed_url: props.toolshedUrl,
            name: props.repo.name,
            owner: props.repo.owner,
            changeset_revision: details.changeset_revision,
        });
        startWatchingResource();
    } catch (e) {
        error.value = errorMessageAsString(e);
    }
}

function startWatchingResource() {
    repositoryWatcher.startWatchingResource();
}

function stopWatchingResource() {
    repositoryWatcher.stopWatchingResource();
}
</script>

<template>
    <b-card>
        <div class="mb-1">{{ repo.long_description }}</div>
        <div class="mb-3">
            <b-link :href="repo.repository_url" target="_blank">Show additional details and dependencies.</b-link>
        </div>
        <div>
            <span v-if="loading">
                <span class="fa fa-spinner fa-spin" />
                <span class="loading-message">Loading repository details...</span>
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
                                @onInstall="setupRepository(row.item)"
                                @onUninstall="uninstallRepository(row.item)" />
                        </template>
                    </b-table>
                    <InstallationSettings
                        v-if="showSettings && selectedChangeset"
                        :repo="repo"
                        :toolshed-url="toolshedUrl"
                        :changeset-revision="selectedChangeset"
                        :requires-panel="selectedRequiresPanel"
                        :current-panel="panel['default']"
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
