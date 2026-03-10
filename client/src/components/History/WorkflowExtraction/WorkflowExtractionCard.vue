<script setup lang="ts">
import { faFile, faFolder } from "@fortawesome/free-regular-svg-icons";
import { faPencilAlt, faWrench } from "@fortawesome/free-solid-svg-icons";
import { computed } from "vue";

import type { WorkflowExtractionJob } from "@/api/histories";
import type { CardBadge, TitleIcon } from "@/components/Common/GCard.types";

import type { WorkflowExtractionInput } from "./types";

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

const props = defineProps<{
    job: WorkflowExtractionInput | WorkflowExtractionJob;
}>();

const emit = defineEmits<{
    (e: "rename"): void;
    (e: "select"): void;
}>();

const badges = computed<CardBadge[]>(() => {
    const badges: CardBadge[] = [];
    if (props.job.step_type === "tool") {
        badges.push({
            id: "step-type",
            label: "Workflow Step",
            icon: faWrench,
            title: "This will be a tool step in the workflow",
            class: "node-header unselectable",
        });
    } else if (props.job.step_type === "input_collection") {
        badges.push(INPUT_IS_RENAMABLE_BADGE);
        badges.push({
            id: "step-type",
            label: "Input Dataset Collection",
            icon: faFolder,
            title: "This will be a dataset collection workflow input",
            class: "node-header unselectable",
        });
    } else {
        badges.push(INPUT_IS_RENAMABLE_BADGE);
        badges.push({
            id: "step-type",
            label: "Input Dataset",
            icon: faFile,
            title: "This will be a dataset workflow input",
            class: "node-header unselectable",
        });
    }
    return badges;
});

const titleIcon = computed<TitleIcon>(() => {
    if (props.job.step_type === "tool") {
        return {
            icon: faWrench,
            title: "Workflow Step",
        };
    }
    return props.job.step_type === "input_collection"
        ? {
              icon: faFolder,
              title: "Input Dataset Collection",
          }
        : {
              icon: faFile,
              title: "Input Dataset",
          };
});
</script>

<template>
    <GCard
        :badges="badges"
        :title="'newName' in props.job ? props.job.newName : props.job.tool_name || 'Unnamed Step'"
        :title-icon="titleIcon"
        :can-rename-title="props.job.step_type !== 'tool' && props.job.checked"
        selectable
        :selected="props.job.checked"
        select-title="Include as a step in the workflow"
        dim-when-unselected
        @rename="emit('rename')"
        @select="emit('select')">
        <template v-if="props.job.outputs?.length" v-slot:description>
            <div v-for="(output, outputIndex) in props.job.outputs" :key="outputIndex">
                <GenericHistoryItem
                    :item-id="output.id"
                    :item-src="output.history_content_type === 'dataset' ? 'hda' : 'hdca'" />
            </div>
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
