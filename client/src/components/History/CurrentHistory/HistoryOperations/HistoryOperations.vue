<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCheckSquare, faCompress } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import type { HistorySummaryExtended } from "@/api";

import DefaultOperations from "@/components/History/CurrentHistory/HistoryOperations/DefaultOperations.vue";

library.add(faCheckSquare, faCompress);

interface Props {
    history: HistorySummaryExtended;
    hasMatches: boolean;
    editable: boolean;
    expandedCount: number;
    showSelection: boolean;
    isMultiViewItem: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits(["update:show-selection", "collapse-all", "update:operation-running"]);

function toggleSelection() {
    emit("update:show-selection", !props.showSelection);
}

function onUpdateOperationStatus(updateTime: number) {
    emit("update:operation-running", updateTime);
}
</script>

<template>
    <section>
        <nav v-if="editable" class="content-operations d-flex justify-content-between bg-secondary">
            <BButtonGroup>
                <BButton
                    v-b-tooltip.hover
                    title="Select Items"
                    class="show-history-content-selectors-btn rounded-0"
                    size="sm"
                    variant="link"
                    :disabled="!hasMatches"
                    :pressed="showSelection"
                    @click="toggleSelection">
                    <FontAwesomeIcon :icon="faCheckSquare" fixed-width />
                </BButton>

                <BButton
                    v-b-tooltip.hover
                    title="Collapse Items"
                    class="rounded-0"
                    size="sm"
                    variant="link"
                    :disabled="!expandedCount"
                    @click="$emit('collapse-all')">
                    <FontAwesomeIcon :icon="faCompress" fixed-width />
                </BButton>
            </BButtonGroup>

            <BButtonGroup v-show="showSelection">
                <slot name="selection-operations" />
            </BButtonGroup>

            <DefaultOperations
                v-if="!isMultiViewItem"
                v-show="!showSelection"
                :history="history"
                @update:operation-running="onUpdateOperationStatus" />
        </nav>
        <nav v-else-if="isMultiViewItem" class="content-operations bg-secondary">
            <BButton
                v-b-tooltip.hover
                title="Collapse Items"
                class="rounded-0"
                size="sm"
                variant="link"
                :disabled="!expandedCount"
                @click="$emit('collapse-all')">
                <FontAwesomeIcon :icon="faCompress" fixed-width />
            </BButton>
        </nav>
    </section>
</template>

<style lang="scss">
// remove borders around buttons in menu
.content-operations .btn-group .btn {
    border-color: transparent !important;
    text-decoration: none;
    border-radius: 0px;
}
</style>
