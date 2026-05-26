<script setup lang="ts">
import { faFile, faFolder } from "@fortawesome/free-regular-svg-icons";
import {
    faBan,
    faExclamationTriangle,
    faInfoCircle,
    faLayerGroup,
    faPencilAlt,
    faWrench,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import type { CardBadge, TitleIcon } from "@/components/Common/GCard.types";

import { isMappedTool, isWorkflowExtractionInput, type WorkflowExtractionRow } from "./types";

import DisplayedItem from "../Content/DisplayedItem.vue";
import GCard from "@/components/Common/GCard.vue";
import GenericHistoryItem from "@/components/History/Content/GenericItem.vue";

/** Badge for renamable workflow inputs. Only applied to workflow inputs, never tool steps. */
const INPUT_IS_RENAMABLE_BADGE: CardBadge = {
    id: "is-renamable-input",
    label: "Renamable",
    icon: faPencilAlt,
    title: "Click the pencil icon next to the step title to rename this workflow input",
    class: "unselectable",
};

/** Metadata for each step type, used for displaying the step type badge and title icon */
const STEP_TYPE_META: Record<
    "tool" | "input_dataset" | "input_collection",
    { icon: typeof faWrench | typeof faFile | typeof faFolder; label: string; title: string }
> = {
    tool: { icon: faWrench, label: "Workflow Step", title: "This will be a tool step in the workflow" },
    input_dataset: { icon: faFile, label: "Input Dataset", title: "This will be a dataset workflow input" },
    input_collection: {
        icon: faFolder,
        label: "Input Dataset Collection",
        title: "This will be a dataset collection workflow input",
    },
};

function mappedBadge(size: number | null | undefined): CardBadge {
    return {
        id: "mapped-tool",
        label: typeof size === "number" ? `Mapped over ${size} items` : "Mapped",
        icon: faLayerGroup,
        title: "This row represents a mapped tool step backed by an implicit collection job.",
        class: "unselectable",
        variant: "info",
    };
}

const props = defineProps<{
    job: WorkflowExtractionRow;
}>();

const emit = defineEmits<{
    (e: "rename"): void;
    (e: "select"): void;
    (e: "view-job", jobId: string): void;
}>();

const badges = computed<CardBadge[]>(() => {
    const badges: CardBadge[] = [];
    const meta = STEP_TYPE_META[props.job.step_type];
    if (props.job.step_type === "tool") {
        if (props.job.id && props.job.invalid !== "custom_tool_inaccessible") {
            badges.push({
                id: "view-job-details",
                label: "View Job",
                icon: faInfoCircle,
                title: "View details for the job that ran this tool",
                handler: () => {
                    emit("view-job", props.job.id!);
                },
                variant: "info",
            });
        }

        if (props.job.invalid === "custom_tool_inaccessible") {
            badges.push({
                id: "custom-tool-inaccessible",
                label: "Custom Tool Inaccessible",
                icon: faBan,
                title: "This history item was produced by a User Defined Tool that is not accessible for you. Hence, this step cannot be included in the workflow.",
                class: "unselectable",
                variant: "danger",
            });
        } else if (props.job.invalid === "tool_missing_or_inaccessible") {
            badges.push({
                id: "tool-missing-or-inaccessible",
                label: "Tool Missing or Inaccessible",
                icon: faExclamationTriangle,
                title: "This history item was produced by a tool that is either missing or inaccessible for you. Hence, this step cannot be included in the workflow.",
                class: "unselectable",
                variant: "danger",
            });
        }

        if (props.job.tool_version_warning) {
            badges.push({
                id: "tool-version-warning",
                label: "Different Tool Version",
                icon: faExclamationTriangle,
                title: props.job.tool_version_warning,
                class: "unselectable",
                variant: "warning",
            });
        }
        if (isMappedTool(props.job)) {
            badges.push(mappedBadge(props.job.implicit_collection_jobs_size));
        }
    } else {
        badges.push(INPUT_IS_RENAMABLE_BADGE);
    }
    badges.push({
        id: "step-type",
        label: meta.label,
        icon: meta.icon,
        title: meta.title,
        class: "node-header unselectable",
    });
    return badges;
});

const titleIcon = computed<TitleIcon>(() => {
    const { icon, label } = STEP_TYPE_META[props.job.step_type];
    return { icon, title: label };
});
</script>

<template>
    <GCard
        :class="{ disabled: Boolean(props.job.invalid) }"
        :badges="badges"
        :title="
            isWorkflowExtractionInput(props.job)
                ? props.job.newName
                : props.job.tool_name || props.job.tool_id || 'Unnamed Step'
        "
        :title-icon="titleIcon"
        :can-rename-title="props.job.step_type !== 'tool' && props.job.checked"
        selectable
        :selected="props.job.checked"
        select-title="Include as a step in the workflow"
        dim-when-unselected
        @rename="emit('rename')"
        @select="emit('select')">
        <template v-slot:select>
            <FontAwesomeIcon
                v-if="Boolean(props.job.invalid)"
                :icon="faExclamationTriangle"
                class="text-danger mr-1"
                fixed-width />
        </template>
        <template v-slot:description>
            <template v-if="props.job.outputs?.length">
                <div v-for="(output, outputIndex) in props.job.outputs" :key="outputIndex">
                    <DisplayedItem
                        v-if="props.job.invalid === 'custom_tool_inaccessible'"
                        :item-id="output.id"
                        :deleted="output.deleted"
                        :hid="output.hid"
                        :history-content-type="output.history_content_type"
                        :name="output.name"
                        :state="output.state" />
                    <GenericHistoryItem
                        v-else
                        :item-id="output.id"
                        :item-src="output.history_content_type === 'dataset' ? 'hda' : 'hdca'" />
                </div>
            </template>
        </template>
    </GCard>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";

.g-card {
    :deep(.node-header) {
        background: $brand-primary;
        color: $white;
        font-weight: normal;
        font-size: 0.8rem;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem 0.25rem 0 0;
    }
}
</style>
