<script setup lang="ts">
import { BCard, BCardTitle } from "bootstrap-vue";

import { borderVariant } from "@/components/Common/Wizard/utils";

import type { RulesCreatingWhat } from "./types";

interface Props {
    selected: boolean;
    creatingWhat: RulesCreatingWhat;
}

defineProps<Props>();

const emit = defineEmits(["select"]);
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
            Fill in URLs/URIs as well as sample sheet in an external workbook using tools like Excel or Google Sheets.
        </div>
    </BCard>
</template>
