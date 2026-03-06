<script setup lang="ts">
import { faFile, faFolder } from "@fortawesome/free-regular-svg-icons";
import { faWrench } from "@fortawesome/free-solid-svg-icons";
import { computed, ref } from "vue";

import type { CardBadge, TitleIcon } from "@/components/Common/GCard.types";

import type { ClientWorkflowExtractionJob } from "./types";

import GCard from "@/components/Common/GCard.vue";
import Heading from "@/components/Common/Heading.vue";
import GenericHistoryItem from "@/components/History/Content/GenericItem.vue";

const props = defineProps<{
    job: ClientWorkflowExtractionJob;
}>();

const emit = defineEmits<{
    (e: "select"): void;
}>();

const collapse = ref(false);

const badges = computed<CardBadge[]>(() => {
    const badges: CardBadge[] = [];
    if (props.job.stepType === "tool") {
        badges.push({
            id: "step-type",
            label: "Workflow Step",
            icon: faWrench,
            title: "This will be a tool step in the workflow",
            class: "node-header",
        });
    } else if (props.job.stepType === "input_collection") {
        badges.push({
            id: "step-type",
            label: "Dataset Collection Input",
            icon: faFolder,
            title: "This will be a dataset collection workflow input",
            class: "node-header",
        });
    } else {
        badges.push({
            id: "step-type",
            label: "Dataset Input",
            icon: faFile,
            title: "This will be a dataset workflow input",
            class: "node-header",
        });
    }
    return badges;
});

const titleIcon = computed<TitleIcon>(() => {
    if (props.job.stepType === "tool") {
        return {
            icon: faWrench,
            title: "Workflow Step",
        };
    }
    return props.job.stepType === "input_collection"
        ? {
              icon: faFolder,
              title: "Dataset Collection Input",
          }
        : {
              icon: faFile,
              title: "Dataset Input",
          };
});
</script>

<template>
    <GCard
        :badges="badges"
        :title="'newName' in props.job ? props.job.newName : props.job.tool_name || 'Unnamed Step'"
        :title-icon="titleIcon"
        :can-rename-title="props.job.stepType !== 'tool'"
        selectable
        :selected="props.job.checked"
        @select="emit('select')">
        <template v-if="props.job.outputs?.length" v-slot:description>
            <Heading
                :collapse="collapse === false ? 'open' : 'closed'"
                separator
                size="sm"
                class="mb-2"
                @click="collapse = !collapse">
                History
                <span v-if="props.job.outputs.length > 1">Items</span>
                <span v-else>Item</span>
                Created
                <span v-if="props.job.outputs.length > 1">({{ props.job.outputs.length }})</span>
            </Heading>
            <transition name="slide">
                <div v-if="!collapse">
                    <div v-for="(output, outputIndex) in props.job.outputs" :key="outputIndex">
                        <GenericHistoryItem
                            :item-id="output.id"
                            :item-src="output.history_content_type === 'dataset' ? 'hda' : 'hdca'" />
                    </div>
                </div>
            </transition>
        </template>
    </GCard>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";

.slide-enter-active,
.slide-leave-active {
    transition: all 0.3s ease;
    max-height: 200px;
    opacity: 1;
    overflow: hidden;
}

.slide-enter-from,
.slide-leave-to {
    max-height: 0;
    opacity: 0;
}

.g-card {
    :deep(.node-header) {
        background: $brand-primary;
        color: $white;
        font-weight: unset;
    }
}
</style>
