<script setup lang="ts">
import {
    faBell,
    faCheck,
    faEdit,
    faExclamationTriangle,
    faExternalLinkAlt,
    faPlay,
    faUpload,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBadge } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, onBeforeUnmount, ref } from "vue";
import { useRouter } from "vue-router";

import type { CuratedWorkflow } from "@/api/curatedWorkflows";
import type { CardAction, CardBadge } from "@/components/Common/GCard.types";
import { compareTrsVersions } from "@/components/Workflow/Import/trsVersion";
import { getRedirectOnImportPath } from "@/components/Workflow/redirectPath";
import { Services } from "@/components/Workflow/services";
import { copyWorkflow } from "@/components/Workflow/workflows.services";
import { Toast } from "@/composables/toast";
import { useCanRequestToolInstallation } from "@/composables/toolInstallationRequest";
import { useUserStore } from "@/stores/userStore";
import { ApiError } from "@/utils/simple-error";

import GCard from "@/components/Common/GCard.vue";
import UtcDate from "@/components/UtcDate.vue";
import ToolInstallationRequestDialog from "@/components/Workflow/ToolInstallationRequestDialog.vue";

interface Props {
    workflow: CuratedWorkflow;
    gridView?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    gridView: false,
});

const emit = defineEmits<{
    (e: "tagClick", tag: string): void;
    (e: "collectionClick", collection: string): void;
}>();

const router = useRouter();
const services = new Services();

const userStore = useUserStore();
const { isAnonymous } = storeToRefs(userStore);

const workflow = computed(() => props.workflow);

const importing = ref(false);
let unmounted = false;
onBeforeUnmount(() => {
    unmounted = true;
});

/** Presence of a stored workflow id means the row is a workflow hosted here, not a catalog entry. */
const isLocal = computed(() => Boolean(workflow.value.stored_workflow_id));

const importTitle = computed(() =>
    isAnonymous.value ? "Log in to import this workflow" : "Import this workflow into your account",
);

const titleBadges = computed<CardBadge[]>(() =>
    (workflow.value.collections ?? []).map((collection: string) => ({
        id: `curated-collection-${collection}`,
        label: collection,
        title: `Part of the ${collection} collection. Click to show the whole collection.`,
        type: "badge",
        variant: "outline-secondary",
        handler: () => emit("collectionClick", collection),
    })),
);

const canRequestTools = useCanRequestToolInstallation();
const canRequestMissingTools = computed(() => canRequestTools.value && Boolean(workflow.value.missing_tools?.length));
const showInstallationRequest = ref(false);
// Only for this visit: the admins' answer arrives as a notification, and the badge clears once they install.
const installationRequested = ref(false);

function onInstallationRequested() {
    installationRequested.value = true;
    Toast.success("Installation request sent. Check your notifications for updates.");
}

/** `toolshed.g2.bx.psu.edu/repos/iuc/fastp/fastp/0.23.4` -> `fastp`; built-in ids pass through. */
function shortToolName(toolId: string): string {
    const parts = toolId.split("/");
    return parts.length > 2 && parts.includes("repos") ? (parts[parts.length - 2] ?? toolId) : toolId;
}

const runnabilityBadge = computed<CardBadge | null>(() => {
    const missingTools = workflow.value.missing_tools;
    // Null means the server didn't check, which is not the same as nothing missing.
    if (missingTools === null || missingTools === undefined) {
        return null;
    }
    if (missingTools.length === 0) {
        return {
            id: "curated-runnable",
            label: "Ready to run",
            title: "Every tool this workflow uses is installed on this Galaxy",
            icon: faCheck,
            variant: "success",
        };
    }
    const names = [...new Set(missingTools.map(shortToolName))];
    const canAsk = canRequestMissingTools.value && !installationRequested.value;
    return {
        id: "curated-missing-tools",
        label: `Needs ${names.length} ${names.length === 1 ? "tool" : "tools"}`,
        title: `Not installed on this Galaxy: ${names.join(", ")}${canAsk ? ". Click to ask the admins to install them." : ""}`,
        icon: faExclamationTriangle,
        variant: "warning",
        handler: canAsk ? () => (showInstallationRequest.value = true) : undefined,
    };
});

// Only what decides whether to pick this workflow sits beside the title; every
// extra badge there competes with the title for the header row.
const badges = computed<CardBadge[]>(() => (runnabilityBadge.value ? [runnabilityBadge.value] : []));

/** Descriptive details, shown in the footer next to the update time. */
const footerBadges = computed<CardBadge[]>(() => {
    const details: CardBadge[] = importedBadge.value ? [importedBadge.value] : [];

    if (workflow.value.number_of_steps !== null && workflow.value.number_of_steps !== undefined) {
        details.push({
            id: "curated-steps",
            label: `${workflow.value.number_of_steps} steps`,
            title: "Number of steps in this workflow",
        });
    }

    if (workflow.value.release) {
        details.push({
            id: "curated-release",
            label: `v${workflow.value.release}`,
            title: "Released version of this workflow",
        });
    }

    return details;
});

/** A catalog row can only be imported if the catalog gave us something to import. */
const canImport = computed(() => (isLocal.value ? true : Boolean(workflow.value.trs_url)));

/** The user's own copy of a catalog workflow, from an earlier import. */
const importedWorkflowId = computed(() => (isLocal.value ? null : workflow.value.imported_workflow_id));

/** Whether a newer release has come out since the user's copy was imported. */
const updateAvailable = computed(() => {
    const imported = workflow.value.imported_version;
    const release = workflow.value.release;
    if (!importedWorkflowId.value || !imported || !release) {
        return false;
    }
    // Only a strictly newer release counts: the catalog can lag a direct TRS import, and an import
    // from the branch (the fallback when a release hadn't reached Dockstore yet) can't be placed at all.
    const comparison = compareTrsVersions(release, imported);
    return comparison !== null && comparison > 0;
});

const importedBadge = computed<CardBadge | null>(() => {
    if (!importedWorkflowId.value) {
        return null;
    }
    if (updateAvailable.value) {
        return {
            id: "curated-update-available",
            label: `You have ${workflow.value.imported_version}`,
            title: `Your copy was imported from ${workflow.value.imported_version}; v${workflow.value.release} is the latest release`,
            variant: "warning",
        };
    }
    return {
        id: "curated-imported",
        label: "In your workflows",
        title: "You have already imported this workflow",
        variant: "info",
    };
});

const importAction = computed<CardAction>(() => ({
    id: "curated-import",
    label: updateAvailable.value ? `Update to v${workflow.value.release}` : "Import",
    icon: faUpload,
    title: !canImport.value
        ? "This workflow cannot be imported automatically"
        : updateAvailable.value
          ? `Import v${workflow.value.release} as a new workflow, alongside your copy`
          : importTitle.value,
    disabled: isAnonymous.value || !canImport.value || importing.value,
    variant: "outline-primary",
    handler: onImport,
}));

const primaryActions = computed<CardAction[]>(() => {
    if (importedWorkflowId.value) {
        const runImported: CardAction = {
            id: "curated-run",
            label: "Run",
            icon: faPlay,
            title: "Run your imported copy of this workflow",
            to: `/workflows/run?id=${importedWorkflowId.value}`,
        };
        // Up to date, another import would just be a duplicate, so it steps back into the menu.
        return updateAvailable.value ? [runImported, importAction.value] : [runImported];
    }

    if (!isLocal.value) {
        return [importAction.value];
    }

    return [
        {
            id: "curated-run",
            label: "Run",
            icon: faPlay,
            title: "Run workflow",
            to: `/workflows/run?id=${workflow.value.stored_workflow_id}`,
        },
        importAction.value,
    ];
});

const extraActions = computed<CardAction[]>(() => {
    if (isLocal.value) {
        return [
            {
                id: "curated-open",
                label: "View workflow",
                title: "View this workflow",
                to: `/published/workflow?id=${workflow.value.stored_workflow_id}`,
            },
        ];
    }

    const actions: CardAction[] = [];

    if (canRequestMissingTools.value) {
        actions.push({
            id: "curated-request-tools",
            label: installationRequested.value ? "Installation requested" : "Request tool installation",
            title: "Ask the admins to install the tools this workflow needs",
            icon: faBell,
            disabled: installationRequested.value,
            handler: () => (showInstallationRequest.value = true),
        });
    }

    if (workflow.value.doi) {
        actions.push({
            id: "curated-doi",
            label: "View DOI",
            title: `Resolve DOI ${workflow.value.doi}`,
            icon: faExternalLinkAlt,
            externalLink: true,
            href: `https://doi.org/${workflow.value.doi}`,
        });
    }

    return actions;
});

/** The IWC page has the diagram and full documentation, so it's worth a visible button rather than a menu entry. */
const secondaryActions = computed<CardAction[]>(() => {
    if (isLocal.value || !workflow.value.external_url) {
        return [];
    }
    return [
        {
            id: "curated-external-link",
            label: "IWC",
            title: "View this workflow on iwc.galaxyproject.org",
            icon: faExternalLinkAlt,
            externalLink: true,
            href: workflow.value.external_url,
            variant: "outline-primary",
        },
    ];
});

async function importFromTrs() {
    try {
        return await services.importTrsToolFromUrl(workflow.value.trs_url);
    } catch (error) {
        // Dockstore can lag a release tag behind the IWC manifest; the branch
        // beats failing outright, and the pinned URL takes over once it syncs.
        if (workflow.value.trs_fallback_url && error instanceof ApiError && error.status === 404) {
            return await services.importTrsToolFromUrl(workflow.value.trs_fallback_url);
        }
        throw error;
    }
}

async function onImport() {
    // Checked here as well as through ``disabled``: a second click can land
    // before the disabled button re-renders.
    if (importing.value) {
        return;
    }
    importing.value = true;
    try {
        await (isLocal.value ? onImportLocal() : onImportTrs());
    } finally {
        importing.value = false;
    }
}

async function onImportTrs() {
    try {
        const response = await importFromTrs();
        if (unmounted) {
            // The user has moved on; redirecting now would yank them off that page.
            Toast.success(`Imported "${workflow.value.name}"`);
            return;
        }
        router.push(getRedirectOnImportPath(response));
    } catch (error) {
        Toast.error(`Failed to import workflow: ${error}`);
    }
}

async function onImportLocal() {
    try {
        await copyWorkflow(workflow.value.stored_workflow_id as string, workflow.value.owner ?? undefined);
        Toast.success("Workflow imported successfully");
    } catch (error) {
        Toast.error(`Failed to import workflow: ${error}`);
    }
}
</script>

<template>
    <GCard
        :id="workflow.id"
        class="curated-workflow-card"
        :title="workflow.name"
        :title-badges="titleBadges"
        :title-n-lines="2"
        :can-rename-title="false"
        :description="workflow.description"
        :grid-view="props.gridView"
        :badges="badges"
        :extra-actions="extraActions"
        :primary-actions="primaryActions"
        :secondary-actions="secondaryActions"
        :selectable="false"
        :show-bookmark="false"
        :tags="workflow.tags"
        :tags-editable="false"
        :max-visible-tags="props.gridView ? 2 : 8"
        @tagClick="(tag: string) => emit('tagClick', tag)">
        <template v-slot:update-time>
            <div :id="`g-card-${workflow.id}-details`" class="align-self-end d-flex flex-gapx-1 flex-wrap mt-1">
                <BBadge v-if="workflow.update_time" v-g-tooltip.hover pill variant="secondary" title="Last updated">
                    <FontAwesomeIcon :icon="faEdit" fixed-width />
                    <UtcDate :date="workflow.update_time" mode="elapsed" />
                </BBadge>
                <BBadge
                    v-for="detail in footerBadges"
                    :id="`g-card-badge-${detail.id}-${workflow.id}`"
                    :key="detail.id"
                    v-g-tooltip.hover
                    pill
                    :variant="detail.variant || 'secondary'"
                    :title="detail.title">
                    {{ detail.label }}
                </BBadge>
            </div>
            <!-- Parked in a slot because the card needs GCard as its root; a <dialog> renders in the top layer anyway. -->
            <ToolInstallationRequestDialog
                v-if="canRequestMissingTools"
                v-model:show="showInstallationRequest"
                :missing-tool-ids="workflow.missing_tools ?? []"
                :workflow-id="isLocal ? (workflow.stored_workflow_id ?? undefined) : undefined"
                :workflow-name="workflow.name"
                :workflow-url="workflow.external_url ?? undefined"
                @submitted="onInstallationRequested" />
        </template>
    </GCard>
</template>
