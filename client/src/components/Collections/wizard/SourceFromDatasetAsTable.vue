<script setup lang="ts">
import { BCard, BCardTitle } from "bootstrap-vue";

import { borderVariant } from "@/components/Common/Wizard/utils";

interface Props {
    selected: boolean;
}

defineProps<Props>();

const emit = defineEmits(["select"]);
</script>

<template>
    <BCard
        data-import-source-from="dataset_as_table"
        class="wizard-selection-card"
        :border-variant="borderVariant(selected)"
        @click="emit('select', 'dataset_as_table')">
        <BCardTitle>
            <b>Dataset As Table</b>
        </BCardTitle>
        <div>
            This option lets you load a list of URIs or any sort of tabular data that can be transformed into a list of
            URIs to describe the datasets and metadata to import from an existing Galaxy dataset.
        </div>
    </BCard>
</template>
