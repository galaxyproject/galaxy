<script setup lang="ts">
import { BCard, BCardGroup, BCardTitle } from "bootstrap-vue";

import { borderVariant } from "@/components/Common/Wizard/utils";

import { type RulesCreatingWhat } from "./types";

interface Props {
    creatingWhat: RulesCreatingWhat;
}

const emit = defineEmits(["onChange"]);

defineProps<Props>();
</script>

<template>
    <BCardGroup deck>
        <BCard
            data-creating-what="datasets"
            class="wizard-selection-card"
            :border-variant="borderVariant(creatingWhat === 'datasets')"
            @click="emit('onChange', 'datasets')">
            <BCardTitle>
                <b>Datasets</b>
            </BCardTitle>
            <div>
                This options lets you import any number of individual Galaxy datasets. These will be unique items in
                your Galaxy history.
            </div>
        </BCard>
        <BCard
            data-creating-what="collections"
            class="wizard-selection-card"
            :border-variant="borderVariant(creatingWhat === 'collections')"
            @click="emit('onChange', 'collections')">
            <BCardTitle>
                <b>Collections</b>
            </BCardTitle>
            <div>This options lets you create or more Galaxy dataset collections.</div>
        </BCard>
    </BCardGroup>
</template>
