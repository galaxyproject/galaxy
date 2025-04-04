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
        data-import-source-from="pasted_table"
        class="wizard-selection-card"
        :border-variant="borderVariant(selected)"
        @click="emit('select', 'pasted_table')">
        <BCardTitle>
            <b>Pasted Table</b>
        </BCardTitle>
        <div>
            This option lets you just paste in a list of URLs/URIs or any sort of tabular data that can be transformed
            into a list of URIs to describe the datasets and metadata to import.
        </div>
    </BCard>
</template>
