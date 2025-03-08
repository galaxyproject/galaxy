<script setup lang="ts">
import { BButton } from "bootstrap-vue";
import { computed, ref } from "vue";

import type { HistoryItemSummary } from "@/api";
import localize from "@/utils/localization";

import { useExtensionFiltering } from "./useExtensionFilter";
import { usePairingSummary } from "./usePairingSummary";

import PairingFilterInputGroup from "./PairingFilterInputGroup.vue";

interface Props {
    elements: HistoryItemSummary[];
    collectionType: "list:paired" | "list:paired_or_unpaired";
    forwardFilter?: string;
    reverseFilter?: string;
    removeExtensions: boolean;
    extensions?: string[];
    mode: "wizard" | "modal";
    showHid: boolean;
}

const emit = defineEmits<{
    (e: "on-apply", forwardFilter: string, reverseFilter: string): void;
    (e: "on-update", forwardFilter: string, reverseFilter: string): void;
    (e: "on-cancel"): void;
}>();

const props = defineProps<Props>();

const currentForwardFilter = ref(props.forwardFilter || "");
const currentReverseFilter = ref(props.reverseFilter || "");
const { currentSummary, summaryText, autoPair } = usePairingSummary<HistoryItemSummary>(props);

const { showElementExtension } = useExtensionFiltering(props);

function summarize() {
    autoPair(props.elements, currentForwardFilter.value, currentReverseFilter.value, props.removeExtensions);
}

summarize();

function onUpdate(forwardFilter: string, reverseFilter: string) {
    currentForwardFilter.value = forwardFilter;
    currentReverseFilter.value = reverseFilter;
    summarize();
    emit("on-update", currentForwardFilter.value, currentReverseFilter.value);
}

const applyButtonTitle = computed(() => localize("Apply Auto Pairing"));
const hasUnmatchedDatasets = computed(() => {
    return (currentSummary.value?.unpaired.length || 0) > 0;
});
const whereIsTheBuilder = computed(() => {
    if (props.mode == "modal") {
        return `back in the main table of this builder after you click '${applyButtonTitle.value}' below'.`;
    } else {
        return "in the table on the next step of this wizard";
    }
});

function onApply() {
    emit("on-apply", currentForwardFilter.value, currentReverseFilter.value);
}
</script>

<template>
    <div class="collection-creator" data-description="auto pairing">
        <div class="middle flex-row flex-row-container">
            <PairingFilterInputGroup
                :forward-filter="currentForwardFilter"
                :reverse-filter="currentReverseFilter"
                @on-update="onUpdate" />
            <div class="summary-text mt-2">
                {{ summaryText }}
            </div>
            <div class="summary-list-header mt-2">Auto-matched Pairs</div>
            <div class="summary-list-description">
                These pairs of datasets have been auto-matched up using the filters above. The will be included as
                dataset pairs in the final list without additional action.
            </div>
            <ol class="summary-list">
                <li v-for="(pair, index) of currentSummary?.pairs" :key="`paired_${index}`">
                    <span v-if="index > 0">,</span>
                    <span class="pair-name">{{ pair.name }}</span> (<span class="direction">FORWARD</span
                    ><span v-if="showHid" class="dataset-hid">{{ pair.forward.hid }}: </span
                    ><span class="dataset-name">{{ pair.forward.name }}</span> | <span class="direction">REVERSE</span
                    ><span v-if="showHid" class="dataset-hid">{{ pair.reverse.hid }}: </span
                    ><span class="dataset-name">{{ pair.reverse.name }}</span
                    >)
                </li>
            </ol>
            <span v-if="hasUnmatchedDatasets">
                <div class="summary-list-header mt-2">Un-matched Datasets</div>
                <div class="summary-list-description">
                    These datasets were not paired automatically. This builder will allow you to match any of pairs of
                    these manually {{ whereIsTheBuilder }}.
                    <span v-if="collectionType == 'list:paired'">
                        All unmatched datasets will not be included in the final list of paired datasets.
                    </span>
                    <span v-else>
                        Any of these datasets will be included in the final list if they are not discarded.
                    </span>
                </div>
                <ol class="summary-list">
                    <li v-for="(unpairedDataset, index) of currentSummary?.unpaired" :key="`unpaired_${index}`">
                        <span v-if="index > 0">,</span>
                        <span v-if="showHid" class="dataset-hid">{{ unpairedDataset.hid }}: </span>
                        <span class="unpaired-dataset-name dataset-name">{{ unpairedDataset.name }}</span>
                        <span
                            v-if="'extension' in unpairedDataset && showElementExtension(unpairedDataset)"
                            class="dataset-extension-wrapper"
                            >(
                            <span class="dataset-extension">{{ unpairedDataset.extension }}</span>
                            )</span
                        >
                    </li>
                </ol>
            </span>
            <span v-else>
                <div class="summary-list-header mt-2">No Un-matched Datasets</div>
                <div class="summary-list-description">
                    All datasets successfully auto-paired, this is generally a good sign Galaxy was able to correctly
                    pair off all supplied datasets using their names.
                </div>
            </span>
        </div>
        <div v-if="mode == 'modal'" class="footer flex-row">
            <div class="actions vertically-spaced d-flex justify-content-between">
                <BButton tabindex="-1" @click="emit('on-cancel')">
                    {{ localize("Cancel") }}
                </BButton>

                <BButton variant="primary" @click="onApply">
                    {{ localize("Apply Auto Pairing") }}
                </BButton>
            </div>
        </div>
    </div>
</template>

<style lang="scss" scoped>
.summary-text {
    font-size: 1rem;
}

.summary-list {
    margin-left: 20px;

    li {
        list-style-type: none;
        display: inline;

        .direction {
            font-variant: small-caps;
            font-weight: normal;
            color: gray;
            font-size: 0.8rem;
            padding-right: 5px;
            display: none;
        }
    }
}

.summary-list-header {
    font-size: 1rem;
    font-weight: bold;
}

.summary-list-description {
    font-size: 0.9rem;
    font-style: italic;
}

.pair-name {
    font-weight: bold;
    font-size: 0.9rem;
}
.unpaired-dataset-name {
    font-weight: bold;
    font-size: 0.9rem;
}

.dataset-extension-wrapper {
    font-style: italic;
}
</style>
