<script setup lang="ts">
import { BCard, BCardTitle } from "bootstrap-vue";
import { computed } from "vue";

import { borderVariant } from "@/components/Common/Wizard/utils";

import type { RulesCreatingWhat } from "./types";

interface Props {
    selected: boolean;
    creatingWhat: RulesCreatingWhat;
}

const props = defineProps<Props>();

const emit = defineEmits(["select"]);

const whatText = computed(() => {
    if (props.creatingWhat == "datasets") {
        return "dataset and metadata";
    } else {
        return "collection element metadata and structure";
    }
});
</script>

<template>
    <BCard
        data-import-source-from="workbook"
        class="wizard-selection-card"
        :border-variant="borderVariant(selected)"
        @click="emit('select', 'workbook')">
        <BCardTitle>
            <b>External Workbook</b>
        </BCardTitle>
        <div>
            This option lets you fill in URLs/URIs in an external workbook using tools like Excel or Google Sheets and
            specify {{ whatText }} in the workbook also.
        </div>
    </BCard>
</template>
