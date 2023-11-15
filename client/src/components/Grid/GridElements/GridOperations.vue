<script setup lang="ts">
import { BLink } from "bootstrap-vue";

import type { FieldOperations, Operation, RowData } from "@/components/Grid/configs/types";

interface Props {
    rowData: RowData;
    operations: FieldOperations;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "execute", operation: Operation): void;
}>();

/**
 * Availibility of operations might required certain conditions
 */
function hasCondition(conditionHandler: (rowData: RowData) => Boolean) {
    return conditionHandler ? conditionHandler(props.rowData) : true;
}
</script>

<template>
    <span>
        <BLink id="grid-operations" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
            <icon icon="caret-down" class="fa-lg" />
            <span class="font-weight-bold">{{ rowData.title }}</span>
        </BLink>
        <div class="dropdown-menu" aria-labelledby="dataset-dropdown">
            <span v-for="(operation, operationIndex) in operations" :key="operationIndex">
                <a
                    v-if="hasCondition(operation.condition)"
                    class="dropdown-item"
                    @click.prevent="$emit('execute', operation)">
                    <icon :icon="operation.icon" />
                    <span v-localize>{{ operation.title }}</span>
                </a>
            </span>
        </div>
    </span>
</template>
