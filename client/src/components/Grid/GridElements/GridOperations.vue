<script setup lang="ts">
import { faCaretDown, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import type { Operation, RowData } from "@/components/Grid/configs/types";
import { useConfig } from "@/composables/config";
import type { GalaxyConfiguration } from "@/stores/configurationStore";

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

function isLoading(loadingHandler?: (rowData: RowData, config: GalaxyConfiguration) => boolean) {
    return loadingHandler ? loadingHandler(props.rowData, config) : false;
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
            <FontAwesomeIcon :icon="faCaretDown" class="fa-lg" />
            <span class="font-weight-bold">{{ title }}</span>
        </button>
        <div class="dropdown-menu" aria-labelledby="grid-operations">
            <span v-for="(operation, operationIndex) in operations" :key="operationIndex">
                <button
                    v-if="operation && (!operation.condition || hasCondition(operation.condition))"
                    class="dropdown-item"
                    :disabled="isLoading(operation.loading)"
                    :data-description="`grid operation ${operation.title.toLowerCase()}`"
                    @click.prevent="emit('execute', operation)">
                    <FontAwesomeIcon
                        :icon="isLoading(operation.loading) ? faSpinner : operation.icon"
                        :spin="isLoading(operation.loading)" />
                    <span v-localize>{{ operation.title }}</span>
                </button>
            </span>
        </div>
    </span>
</template>
