<script setup lang="ts">
import { BCard, BCol, BContainer, BLink, BRow, BTable } from "bootstrap-vue";
import { computed, ref } from "vue";

import type { HDASummary } from "@/api";

import type { DatasetPair } from "../History/adapters/buildCollectionModal";

const hideUnmatched = ref(false);

interface Props {
    generatedPairs: DatasetPair[];
    workingElements: HDASummary[];
}

const FIELDS = [
    {
        key: "identifier",
        label: "List Identifier",
    },
    {
        key: "forward",
        label: "First Dataset",
    },
    {
        key: "reverse",
        label: "Second Dataset",
    },
];

const UNMATCH_FIELDS = [
    {
        key: "name",
        label: "Unpaired Dataset",
    },
];

const pairedItems = computed(() => {
    return props.generatedPairs.map((e) => {
        return { identifier: e.name, forward: e.forward.name, reverse: e.reverse.name };
    });
});

const unpairedItems = computed(() => {
    return props.workingElements.map((e) => {
        return { name: e.name };
    });
});

const showUnpairedItems = computed(() => {
    return !hideUnmatched.value && unpairedItems.value.length > 0;
});

const summaryText = computed(() => {
    const numMatchedText = `Auto-matched ${props.generatedPairs.length} pair(s) of datasets from target datasets.`;
    const numUnmatched = props.workingElements.length;
    let numUnmatchedText = "";
    if (numUnmatched > 0) {
        numUnmatchedText = `${numUnmatched} dataset(s) were not paired and will not be included in the resulting list of pairs.`;
    }
    return `${numMatchedText} ${numUnmatchedText}`;
});

function clickHideUnmatched() {
    hideUnmatched.value = true;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "correctPairing"): void;
    (e: "correctIdentifiers"): void;
}>();
</script>

<template>
    <BCard no-body>
        <BContainer style="max-width: 100%">
            <BRow>
                <BCol>
                    <p>{{ summaryText }}</p>
                </BCol>
            </BRow>
            <BRow cols="12">
                <BCol :cols="showUnpairedItems ? 8 : 12">
                    <BTable
                        sticky-header
                        striped
                        hover
                        :items="pairedItems"
                        :fields="FIELDS"
                        :outlined="true"
                        class="summary-table"
                        :caption-top="true"
                        :bordered="true">
                        <template v-slot:table-caption
                            ><i class="text-muted"
                                >These pairs will make up the list of pairs being created.</i
                            ></template
                        >
                    </BTable>
                </BCol>
                <BCol v-if="showUnpairedItems" cols="4">
                    <BTable
                        sticky-header
                        striped
                        hover
                        :items="unpairedItems"
                        :fields="UNMATCH_FIELDS"
                        thead-class="d-none"
                        :outlined="true"
                        class="summary-table"
                        :caption-top="true"
                        :bordered="true">
                        <template v-slot:table-caption
                            ><i class="text-muted"
                                >These datasets could not be auto-paired and will not appear in the created collection.
                                <BLink @click="clickHideUnmatched">Hide this.</BLink></i
                            ></template
                        >
                    </BTable>
                </BCol>
            </BRow>
            <BRow>
                <BCol>
                    If this doesn't look correct, it can be manually fixed. Just let us know how it is incorrect.
                    <b><BLink @click="emit('correctPairing')">The pairing is wrong</BLink></b> (datasets were not
                    matched properly or datasets were not included in the matches that should be) or
                    <b
                        ><BLink @click="emit('correctIdentifiers')"
                            >the list identifiers were derived incorrectly</BLink
                        ></b
                    >.
                </BCol>
            </BRow>
        </BContainer>
    </BCard>
</template>

<style lang="scss" scoped></style>
