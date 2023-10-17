<script setup lang="ts">
import axios from "axios";
import { BAlert } from "bootstrap-vue";
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { withPrefix } from "@/utils/redirect";

import { registry } from "./configs/registry";
import { FieldKeyHandler, Operation, RowData } from "./configs/types";

import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";
//@ts-ignore
import UtcDate from "@/components/UtcDate.vue";

const router = useRouter();

interface Props {
    // specifies the grid config identifier as specified in the registry
    id: string;
}

const props = withDefaults(defineProps<Props>(), {});

// contains the current grid data provided by the corresponding api endpoint
const gridData = ref();

// message references
const errorMessage = ref("");
const operationMessage = ref("");
const operationStatus = ref("");

// current grid configuration
const gridConfig = computed(() => {
    return registry[props.id];
});

/**
 * Request grid data
 */
async function getGridData() {
    if (gridConfig.value) {
        try {
            const { data } = await axios.get(withPrefix(gridConfig.value.url));
            gridData.value = data;
            errorMessage.value = "";
        } catch (e) {
            errorMessage.value = "Failed to obtain grid data.";
        }
    }
}

/**
 * Initialize grid data
 */
onMounted(() => {
    getGridData();
});

/**
 * Execute grid operation and display message if available
 */
async function executeOperation(operation: Operation, rowData: RowData) {
    const response = await operation.handler(rowData, router);
    if (response) {
        await getGridData();
        operationMessage.value = response.message;
        operationStatus.value = response.status || "success";
    }
}

/**
 * Process tag inputs
 */
async function onTagInput(data: RowData, tags: Array<string>, tagsHandler: FieldKeyHandler) {
    await tagsHandler({ ...data, tags: tags });
    data.tags = tags;
}

function onTagClick() {}
</script>

<template>
    <div>
        <BAlert v-if="!!errorMessage" variant="danger" show>{{ errorMessage }}</BAlert>
        <BAlert v-if="!!operationMessage" :variant="operationStatus" show>{{ operationMessage }}</BAlert>
        <div>
            <h1 class="mb-3 h-lg">
                {{ gridConfig.title }}
            </h1>
            <table class="table table-striped">
                <thead>
                    <th v-for="(fieldEntry, fieldIndex) in gridConfig.fields" :key="fieldIndex">
                        {{ fieldEntry.title || fieldEntry.key }}
                    </th>
                </thead>
                <tr v-for="(rowData, rowIndex) in gridData" :key="rowIndex">
                    <td v-for="(fieldEntry, fieldIndex) in gridConfig.fields" :key="fieldIndex">
                        <span v-if="!!fieldEntry.operations">
                            <b-dropdown text="Selection" size="sm" variant="primary" data-description="grid operations">
                                <template v-slot:button-content>
                                    <span>
                                        {{ rowData.title }}
                                    </span>
                                </template>
                                <b-dropdown-item
                                    v-for="(operation, operationIndex) in fieldEntry.operations"
                                    :key="operationIndex"
                                    @click="executeOperation(operation, rowData)">
                                    <span v-localize>{{ operation.title }}</span>
                                </b-dropdown-item>
                            </b-dropdown>
                        </span>
                        <span v-else-if="fieldEntry.type == 'string'">
                            {{ rowData[fieldEntry.key] }}
                        </span>
                        <a v-else-if="fieldEntry.type == 'link'" :href="rowData[fieldEntry.key]">
                            {{ rowData[fieldEntry.key] }}
                        </a>
                        <span v-else-if="fieldEntry.type == 'sharing'">
                            {{ rowData.published }}
                        </span>
                        <span v-else-if="fieldEntry.type == 'date'">
                            <UtcDate :date="rowData[fieldEntry.key]" mode="elapsed" />
                        </span>
                        <span v-else-if="fieldEntry.type == 'tags'">
                            <StatelessTags
                                clickable
                                :value="rowData[fieldEntry.key]"
                                :disabled="rowData.published"
                                @input="(tags) => onTagInput(rowData, tags, fieldEntry.handler)"
                                @tag-click="onTagClick" />
                        </span>
                    </td>
                </tr>
            </table>
        </div>
    </div>
</template>
