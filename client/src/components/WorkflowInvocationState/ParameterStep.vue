<script setup lang="ts">
import { BTable } from "bootstrap-vue";

import type { InvocationInputParameter } from "@/api/invocations";

const props = defineProps<{
    parameters: InvocationInputParameter[];
    styledTable?: boolean;
}>();
</script>

<template>
    <BTable
        small
        :outlined="props.styledTable"
        :striped="props.styledTable"
        :borderless="props.styledTable"
        :fields="['label', 'parameter_value']"
        :items="props.parameters">
        <template v-slot:cell(parameter_value)="{ item }">
            <i v-if="item.parameter_value === null || item.parameter_value === undefined" class="text-muted">
                No value provided
            </i>
            <span v-else>
                {{ item.parameter_value }}
            </span>
        </template>
    </BTable>
</template>
