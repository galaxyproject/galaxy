<script setup lang="ts">
import { faDownload, faEnvelope, faWrench } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BProgress } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import {
    getWorkflowToolAvailability,
    installWorkflowTools,
    requestWorkflowToolInstallation,
    type ToolShedRepositoryReference,
    type UnavailableWorkflowTool,
    type WorkflowToolAvailability,
} from "@/api/workflows";
import { Toast } from "@/composables/toast";
import { errorMessageAsString } from "@/utils/simple-error";

import GButton from "@/components/BaseComponents/GButton.vue";
import GModal from "@/components/BaseComponents/GModal.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const props = defineProps<{
    workflowId: string;
    /** Set to open the dialog. */
    show: boolean;
}>();

const emit = defineEmits<{
    (e: "update:show", show: boolean): void;
    /** The user asked to switch the workflow to the tool versions that are installed. */
    (e: "useInstalledVersions"): void;
}>();

const availability = ref<WorkflowToolAvailability | null>(null);
const loading = ref(false);
const working = ref(false);
const errorMessage = ref<string | null>(null);
const requestOutcome = ref<string | null>(null);
/** Set while installing, so the dialog can say which repository it is on. */
const installProgress = ref<{ done: number; total: number; current: string } | null>(null);

const unavailableTools = computed(() => availability.value?.unavailable_tools ?? []);
const canInstall = computed(() => availability.value?.can_install ?? false);
/** The distinct repositories to install, since several tools often come from one repository. */
const installableRepositories = computed(() => {
    const repositories: ToolShedRepositoryReference[] = [];
    for (const tool of unavailableTools.value) {
        const repository = tool.repository;
        if (!repository) {
            continue;
        }
        const seen = repositories.some(
            (other) =>
                other.tool_shed === repository.tool_shed &&
                other.owner === repository.owner &&
                other.name === repository.name,
        );
        if (!seen) {
            repositories.push(repository);
        }
    }
    return repositories;
});
/** Tools an installed version could stand in for without a known change in behaviour. */
const substitutableTools = computed(() => unavailableTools.value.filter((tool) => tool.substitute_version));

async function load() {
    loading.value = true;
    errorMessage.value = null;
    try {
        availability.value = await getWorkflowToolAvailability(props.workflowId);
    } catch (error) {
        errorMessage.value = errorMessageAsString(error);
    } finally {
        loading.value = false;
    }
}

watch(
    () => [props.show, props.workflowId] as const,
    ([show]) => {
        if (show) {
            requestOutcome.value = null;
            load();
        }
    },
    { immediate: true },
);

function describe(tool: UnavailableWorkflowTool) {
    const installedVersions = tool.installed_versions ?? [];
    if (installedVersions.length === 0) {
        return "not installed";
    }
    const installed = installedVersions.join(", ");
    if (tool.substitute_version) {
        return `version ${tool.substitute_version} is installed and can be used instead`;
    }
    return `installed here as ${installed}, which Galaxy cannot vouch for as a replacement`;
}

/**
 * Installs one repository at a time. Installing them in a single request gives no sign of
 * progress for minutes and loses everything if one of them fails, and a tool shed install is
 * slow enough that both matter.
 */
async function onInstall() {
    const repositories = installableRepositories.value;
    working.value = true;
    errorMessage.value = null;
    const failures: string[] = [];
    try {
        for (const [index, repository] of repositories.entries()) {
            installProgress.value = {
                done: index,
                total: repositories.length,
                current: `${repository.owner}/${repository.name}`,
            };
            try {
                const response = await installWorkflowTools(props.workflowId, [repository]);
                for (const entry of response.failed ?? []) {
                    failures.push(`${entry.repository.owner}/${entry.repository.name}: ${entry.error}`);
                }
            } catch (error) {
                failures.push(`${repository.owner}/${repository.name}: ${errorMessageAsString(error)}`);
            }
        }
        installProgress.value = { done: repositories.length, total: repositories.length, current: "" };
        if (failures.length > 0) {
            errorMessage.value = failures.join("\n");
        } else {
            Toast.success("Installed the tools this workflow was missing.");
        }
        await load();
    } finally {
        working.value = false;
        installProgress.value = null;
    }
}

async function onRequestInstallation() {
    working.value = true;
    errorMessage.value = null;
    try {
        const response = await requestWorkflowToolInstallation(props.workflowId);
        const admins = (response.notified_admins ?? []).join(", ");
        const emailed = response.emailed
            ? "They have been emailed about it."
            : "This Galaxy cannot send email, so they will see it the next time they log in.";
        requestOutcome.value = `The workflow has been shared with ${admins}. ${emailed}`;
    } catch (error) {
        errorMessage.value = errorMessageAsString(error);
    } finally {
        working.value = false;
    }
}

function onUseInstalledVersions() {
    emit("update:show", false);
    emit("useInstalledVersions");
}
</script>

<template>
    <GModal
        :show="show"
        title="This workflow needs tools that are not installed"
        size="medium"
        footer
        @update:show="emit('update:show', $event)">
        <div class="workflow-missing-tools">
            <LoadingSpan v-if="loading" message="Checking which tools this workflow needs" />

            <template v-else>
                <div v-if="installProgress" class="install-progress">
                    <BProgress :value="installProgress.done" :max="installProgress.total" animated show-progress />
                    <span>
                        Installing {{ Math.min(installProgress.done + 1, installProgress.total) }} of
                        {{ installProgress.total
                        }}<span v-if="installProgress.current"> : {{ installProgress.current }}</span
                        >. This can take a few minutes per tool.
                    </span>
                </div>

                <BAlert v-if="errorMessage" variant="danger" show>{{ errorMessage }}</BAlert>
                <BAlert v-if="requestOutcome" variant="success" show>{{ requestOutcome }}</BAlert>

                <BAlert v-if="unavailableTools.length === 0" variant="success" show>
                    Every tool this workflow uses is installed in the version the workflow asks for.
                </BAlert>

                <template v-else>
                    <ul class="missing-tool-list">
                        <li v-for="tool in unavailableTools" :key="tool.tool_id" class="missing-tool">
                            <FontAwesomeIcon :icon="faWrench" fixed-width />
                            <span class="missing-tool-id">{{ tool.tool_id }}</span>
                            <span v-if="tool.tool_version" class="missing-tool-version">
                                version {{ tool.tool_version }}
                            </span>
                            <span class="missing-tool-state">{{ describe(tool) }}</span>
                        </li>
                    </ul>

                    <BAlert v-if="!canInstall && availability?.cannot_install_reason" variant="info" show>
                        {{ availability.cannot_install_reason }}
                    </BAlert>
                </template>
            </template>
        </div>

        <template v-slot:footer>
            <GButton v-if="substitutableTools.length > 0" :disabled="working" @click="onUseInstalledVersions">
                Use the installed versions
            </GButton>
            <GButton
                v-if="canInstall && installableRepositories.length > 0"
                color="blue"
                :disabled="working"
                @click="onInstall">
                <FontAwesomeIcon :icon="faDownload" fixed-width />
                {{ working ? "Installing..." : `Install ${installableRepositories.length} missing tools` }}
            </GButton>
            <GButton
                v-if="!canInstall && unavailableTools.length > 0"
                color="blue"
                :disabled="working || !!requestOutcome"
                @click="onRequestInstallation">
                <FontAwesomeIcon :icon="faEnvelope" fixed-width />
                Ask an administrator to install them
            </GButton>
            <GButton transparent @click="emit('update:show', false)">Close</GButton>
        </template>
    </GModal>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";

.install-progress {
    margin-bottom: 0.5rem;

    span {
        color: $text-muted;
    }
}

.missing-tool-list {
    list-style: none;
    margin: 0;
    padding: 0;
}

.missing-tool {
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
    padding: 0.25rem 0;
    border-bottom: 1px solid $border-color;
}

.missing-tool-id {
    word-break: break-all;
}

.missing-tool-version,
.missing-tool-state {
    color: $text-muted;
    white-space: nowrap;
}

.missing-tool-state {
    margin-left: auto;
}
</style>
