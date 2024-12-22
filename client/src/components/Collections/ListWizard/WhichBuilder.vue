<script setup lang="ts">
import { BCard, BCardGroup, BCardTitle } from "bootstrap-vue";

import { borderVariant } from "@/components/Common/Wizard/utils";

import { type WhichListBuilder } from "./types";

interface Props {
    value: WhichListBuilder;
}

const emit = defineEmits(["onChange"]);

defineProps<Props>();
</script>

<template>
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
                This options creates a uniform list of paired datasets, use this option if all of your data should be
                paired off.
            </div>
        </BCard>
        <BCard
            data-which-builder="rules"
            class="wizard-selection-card"
            :border-variant="borderVariant(value === 'rules')"
            @click="emit('onChange', 'rules')">
            <BCardTitle>
                <b>Rule Builder</b>
            </BCardTitle>
            <div>
                The rule builder allows building arbitrarily nested collections of data with reproducible metadata
                parsing and other advanced features.
            </div>
        </BCard>
    </BCardGroup>
</template>
