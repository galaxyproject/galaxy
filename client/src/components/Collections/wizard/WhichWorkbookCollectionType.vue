<script setup lang="ts">
import { BCard, BCardGroup, BCardTitle } from "bootstrap-vue";

import { borderVariant } from "@/components/Common/Wizard/utils";

import type { ParsedFetchWorkbookForCollectionCollectionType } from "./types";

interface Props {
    value: ParsedFetchWorkbookForCollectionCollectionType;
}

const emit = defineEmits(["onChange"]);

defineProps<Props>();
</script>

<template>
    <div>
        <BCardGroup deck>
            <BCard
                data-which-builder="list"
                class="wizard-selection-card"
                :border-variant="borderVariant(value === 'list')"
                @click="emit('onChange', 'list')">
                <BCardTitle>
                    <b>Flat List</b>
                </BCardTitle>
                <div>
                    This options creates a simple flat list of files. If your data isn't nested and does not contained
                    paired datasets, this is the the option to choose.
                </div>
            </BCard>
            <BCard
                data-which-builder="list:paired"
                class="wizard-selection-card"
                :border-variant="borderVariant(value === 'list:paired')"
                @click="emit('onChange', 'list:paired')">
                <BCardTitle>
                    <b>List of Paired Datasets</b>
                </BCardTitle>
                <div>
                    This options creates a uniform list of paired datasets, use this option if all of your data should
                    be paired off.
                </div>
            </BCard>
        </BCardGroup>
        <span>
            <BCardGroup deck class="mt-3">
                <BCard
                    data-which-builder="list:paired_or_unpaired"
                    class="wizard-selection-card"
                    :border-variant="borderVariant(value === 'list:paired_or_unpaired')"
                    @click="emit('onChange', 'list:paired_or_unpaired')">
                    <BCardTitle>
                        <b>Mixed List of Paired and Unpaired Datasets</b>
                    </BCardTitle>
                    <div>
                        For studies that have a mix of paired and unpaired data, this may be the right choice. Existing
                        tools and workflows may have to be updated to allow this modality though.
                    </div>
                </BCard>
                <BCard
                    data-which-builder="list:list"
                    class="wizard-selection-card"
                    :border-variant="borderVariant(value === 'list:list')"
                    @click="emit('onChange', 'list:list')">
                    <BCardTitle>
                        <b>Nested List of Datasets</b>
                    </BCardTitle>
                    <div>
                        A nested list of datasets. This type of collection is a list where each element is in turn a
                        list of datasets. The outer list identifier might group samples together by condition, sample
                        type, etc..
                    </div>
                </BCard>
                <BCard
                    data-which-builder="list:list:paired"
                    class="wizard-selection-card"
                    :border-variant="borderVariant(value === 'list:list:paired')"
                    @click="emit('onChange', 'list:list:paired')">
                    <BCardTitle>
                        <b>Nested List of Dataset Pairs</b>
                    </BCardTitle>
                    <div>
                        A nested list of datasets. This type of collection is a list where each element is in turn a
                        list of pairs of datasets.
                    </div>
                </BCard>
            </BCardGroup>
        </span>
    </div>
</template>
