<script setup lang="ts">
import {
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
import { getRedirectOnImportPath } from "@/components/Workflow/redirectPath";
import { Services } from "@/components/Workflow/services";
import { copyWorkflow } from "@/components/Workflow/workflows.services";
import { Toast } from "@/composables/toast";
import { useUserStore } from "@/stores/userStore";
import { ApiError } from "@/utils/simple-error";

import GCard from "@/components/Common/GCard.vue";
import UtcDate from "@/components/UtcDate.vue";

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
    return {
        id: "curated-missing-tools",
        label: `Needs ${names.length} ${names.length === 1 ? "tool" : "tools"}`,
        title: `Not installed on this Galaxy: ${names.join(", ")}`,
        icon: faExclamationTriangle,
        variant: "warning",
    };
});

// Only what decides whether to pick this workflow sits beside the title; every
// extra badge there competes with the title for the header row.
const badges = computed<CardBadge[]>(() => (runnabilityBadge.value ? [runnabilityBadge.value] : []));

/** Descriptive details, shown in the footer next to the update time. */
const footerBadges = computed<CardBadge[]>(() => {
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

/** A catalog row can only be imported if the catalog gave us something to import. */
const canImport = computed(() => (isLocal.value ? true : Boolean(workflow.value.trs_url)));

const primaryActions = computed<CardAction[]>(() => {
    const importAction: CardAction = {
        id: "curated-import",
        label: "Import",
        icon: faUpload,
        title: canImport.value ? importTitle.value : "This workflow cannot be imported automatically",
        disabled: isAnonymous.value || !canImport.value || importing.value,
        variant: "outline-primary",
        handler: onImport,
    };

    if (!isLocal.value) {
        return [importAction];
    }

    return [
        {
            id: "curated-run",
            label: "Run",
            icon: faPlay,
            title: "Run workflow",
            to: `/workflows/run?id=${workflow.value.stored_workflow_id}`,
        },
        importAction,
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

    if (!workflow.value.doi) {
        return [];
    }
    return [
        {
            id: "curated-doi",
            label: "View DOI",
            title: `Resolve DOI ${workflow.value.doi}`,
            icon: faExternalLinkAlt,
            externalLink: true,
            href: `https://doi.org/${workflow.value.doi}`,
        },
    ];
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
                    variant="secondary"
                    :title="detail.title">
                    {{ detail.label }}
                </BBadge>
            </div>
        </template>
    </GCard>
</template>
