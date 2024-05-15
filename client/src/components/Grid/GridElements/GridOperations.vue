<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCaretDown } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import type { Operation, RowData } from "@/components/Grid/configs/types";
import { useConfig } from "@/composables/config";
import type { GalaxyConfiguration } from "@/stores/configurationStore";

library.add(faCaretDown);

const { config, isConfigLoaded } = useConfig();

interface Props {
    rowData: RowData;
    operations: Array<Operation>;
    title: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "execute", operation: Operation): void;
}>();

/**
 * Availibility of operations might required certain conditions
 */
function hasCondition(conditionHandler: (rowData: RowData, config: GalaxyConfiguration) => Boolean) {
    return conditionHandler ? conditionHandler(props.rowData, config) : true;
}
</script>

<template>
    <span v-if="isConfigLoaded">
        <button
            id="grid-operations"
            data-toggle="dropdown"
            aria-haspopup="true"
            aria-expanded="false"
            class="ui-link font-weight-bold text-nowrap">
            <FontAwesomeIcon icon="caret-down" class="fa-lg" />
            <span class="font-weight-bold">{{ title }}</span>
        </button>
        <div class="dropdown-menu" aria-labelledby="grid-operations">
            <span v-for="(operation, operationIndex) in operations" :key="operationIndex">
                <button
                    v-if="operation && (!operation.condition || hasCondition(operation.condition))"
                    class="dropdown-item"
                    :data-description="`grid operation ${operation.title.toLowerCase()}`"
                    @click.prevent="emit('execute', operation)">
                    <icon :icon="operation.icon" />
                    <span v-localize>{{ operation.title }}</span>
                </button>
            </span>
        </div>
    </span>
</template>
