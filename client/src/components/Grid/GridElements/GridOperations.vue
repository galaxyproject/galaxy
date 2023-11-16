<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCaretDown } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import type { Operation, RowData } from "@/components/Grid/configs/types";

library.add(faCaretDown);

interface Props {
    rowData: RowData;
    operations: Array<Operation>;
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
        <button
            id="grid-operations"
            data-toggle="dropdown"
            aria-haspopup="true"
            aria-expanded="false"
            class="ui-link font-weight-bold">
            <FontAwesomeIcon icon="caret-down" class="fa-lg" />
            <span class="font-weight-bold">{{ rowData.title }}</span>
        </button>
        <div v-if="operations" class="dropdown-menu" aria-labelledby="dataset-dropdown">
            <span v-for="(operation, operationIndex) in operations" :key="operationIndex">
                <button
                    v-if="operation && operation.condition && hasCondition(operation.condition)"
                    class="dropdown-item"
                    @click.prevent="emit('execute', operation)">
                    <icon :icon="operation.icon" />
                    <span v-localize>{{ operation.title }}</span>
                </button>
            </span>
        </div>
    </span>
</template>
