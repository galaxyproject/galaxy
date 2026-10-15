<script setup lang="ts">
import {
    faBell,
    faCheck,
    faExclamationTriangle,
    faExternalLinkAlt,
    faPlay,
    faUpload,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
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

interface Props {
    workflow: CuratedWorkflow;
    gridView?: boolean;
    /** The user already asked the admins for this workflow's tools during this visit. */
    installationRequested?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    gridView: false,
    installationRequested: false,
});

const emit = defineEmits<{
    (e: "tagClick", tag: string): void;
    (e: "collectionClick", collection: string): void;
    (e: "requestTools", workflow: CuratedWorkflow): void;
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

function requestTools() {
    emit("requestTools", workflow.value);
}

/** `toolshed.g2.bx.psu.edu/repos/iuc/fastp/fastp/0.23.4` -> `fastp`; built-in ids pass through. */
function shortToolName(toolId: string): string {
    const parts = toolId.split("/");
    return parts.length > 2 && parts.includes("repos") ? (parts[parts.length - 2] ?? toolId) : toolId;
}

// Null missing_tools means the server didn't check, which is not the same as nothing missing.
const runnableBadge = computed<CardBadge | null>(() =>
    workflow.value.missing_tools?.length === 0
        ? {
              id: "curated-runnable",
              label: "Ready to run",
              title: "Every tool this workflow uses is installed on this Galaxy",
              icon: faCheck,
              variant: "success",
          }
        : null,
);

// On most instances nearly every catalog workflow is missing something, so a warning
// color on each card says nothing; it sits in the quiet footer line and only the
// good news gets color.
const missingToolsDetail = computed<CardBadge | null>(() => {
    const missingTools = workflow.value.missing_tools;
    if (!missingTools?.length) {
        return null;
    }
    const names = [...new Set(missingTools.map(shortToolName))];
    const canAsk = canRequestMissingTools.value && !props.installationRequested;
    return {
        id: "curated-missing-tools",
        label: `Needs ${names.length} ${names.length === 1 ? "tool" : "tools"}`,
        title: `Not installed on this Galaxy: ${names.join(", ")}${canAsk ? ". Click to ask the admins to install them." : ""}`,
        icon: faExclamationTriangle,
        variant: "warning",
        handler: canAsk ? requestTools : undefined,
    };
});

// Only the good news gets a badge beside the title; every extra badge there
// competes with the title for the header row.
const badges = computed<CardBadge[]>(() => (runnableBadge.value ? [runnableBadge.value] : []));

/** Where this workflow stands for this user, shown above the descriptive details. */
const statusDetails = computed<CardBadge[]>(() =>
    [missingToolsDetail.value, importedBadge.value].filter((detail): detail is CardBadge => Boolean(detail)),
);

/** Descriptive details, on a muted line after the update time. */
const metaDetails = computed<CardBadge[]>(() => {
    const details: CardBadge[] = [];

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

/** IWC descriptions are plain text, but local annotations can carry markup; the card shows two lines of text either way. */
const plainDescription = computed(() => {
    // Parsing rather than a tag regex, so the entities sanitize_html escapes (&amp;) decode too.
    const text = new DOMParser().parseFromString(workflow.value.description ?? "", "text/html").body.textContent;
    return (text ?? "").replace(/\s+/g, " ").trim();
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
            icon: faCheck,
        };
    }
    return {
        id: "curated-imported",
        label: "In your workflows",
        title: "You have already imported this workflow",
        icon: faCheck,
    };
});

const importAction = computed<CardAction>(() => ({
    id: "curated-import",
    // Not "Update": this imports a second copy, it doesn't upgrade the one the user has.
    label: updateAvailable.value ? `Import v${workflow.value.release}` : "Import",
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
        // Up to date, importing again only hands back this copy (the server matches on TRS id and version).
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
            label: props.installationRequested ? "Installation requested" : "Request tool installation",
            title: "Ask the admins to install the tools this workflow needs",
            icon: faBell,
            disabled: props.installationRequested,
            handler: requestTools,
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
        :tags="props.gridView ? [] : workflow.tags"
        :tags-editable="false"
        :max-visible-tags="8"
        @tagClick="(tag: string) => emit('tagClick', tag)">
        <template v-slot:description>
            <p v-if="plainDescription" class="curated-description" :title="plainDescription">
                {{ plainDescription }}
            </p>
        </template>
        <template v-slot:update-time>
            <div :id="`g-card-${workflow.id}-details`" class="curated-details">
                <ul v-if="statusDetails.length" class="curated-detail-line">
                    <li
                        v-for="detail in statusDetails"
                        :id="`g-card-badge-${detail.id}-${workflow.id}`"
                        :key="detail.id"
                        v-g-tooltip.hover
                        :title="detail.title">
                        <component
                            :is="detail.handler ? 'button' : 'span'"
                            :type="detail.handler ? 'button' : undefined"
                            :class="{ 'curated-detail-button': detail.handler }"
                            @click="detail.handler && detail.handler()">
                            <FontAwesomeIcon
                                v-if="detail.icon"
                                :icon="detail.icon"
                                :class="detail.variant ? `text-${detail.variant}` : undefined" />
                            {{ detail.label }}
                        </component>
                    </li>
                </ul>
                <ul class="curated-detail-line">
                    <li v-if="workflow.update_time" v-g-tooltip.hover title="Last updated">
                        Updated <UtcDate :date="workflow.update_time" mode="elapsed" />
                    </li>
                    <li
                        v-for="detail in metaDetails"
                        :id="`g-card-badge-${detail.id}-${workflow.id}`"
                        :key="detail.id"
                        v-g-tooltip.hover
                        :title="detail.title">
                        {{ detail.label }}
                    </li>
                </ul>
            </div>
        </template>
    </GCard>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";

.curated-description {
    display: -webkit-box;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
    overflow: hidden;
    margin: 0;
    color: $text-muted;
}

.curated-details {
    align-self: flex-end;
    margin-top: 0.25rem;
    font-size: var(--font-size-small);
    color: $text-muted;
}

.curated-detail-line {
    display: flex;
    flex-wrap: wrap;
    margin: 0;
    padding: 0;
    list-style: none;

    li + li::before {
        content: "\00b7";
        margin: 0 0.4rem;
    }
}

.curated-detail-button {
    padding: 0;
    border: 0;
    background: none;
    color: inherit;
    text-decoration: underline dotted;
    text-underline-offset: 2px;
}
</style>
