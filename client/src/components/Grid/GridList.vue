<script setup lang="ts">
import axios from "axios";
import { BAlert } from "bootstrap-vue";
//@ts-ignore
import UtcDate from "components/UtcDate";
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { withPrefix } from "@/utils/redirect";

const router = useRouter();

interface Props {
    name: string;
}

const props = withDefaults(defineProps<Props>(), {});

const gridData = ref();
const errorMessage = ref("");
const operationMessage = ref("");

interface configType {
    url: string;
    resource: string;
    item: string;
    plural: string;
    title: string;
}

const config: Record<string, configType> = {
    visualizations: {
        url: "/api/visualizations?view=detailed&sharing=true",
        resource: "visualizations",
        item: "visualization",
        plural: "Visualizations",
        title: "Visualizations",
    }
}

const fields = [
    {
        title: "title",
        operations: [
            {
                title: "Edit Attributes",
                handler: (data: any) => {
                    router.push(`/visualizations/edit?id=${data.id}`);
                },
            },
            {
                title: "Share and Publish",
                handler: (data: any) => {
                    router.push(`/visualizations/sharing?id=${data.id}`);
                },
            },
            {
                title: "Delete",
                handler: (data: any) => {
                    return `'${data.title}' has been deleted.`;
                },
            },
        ],
    },
    {
        key: "type",
        type: "string",
    },
    {
        key: "create_time",
        type: "date",
    },
    {
        key: "update_time",
        type: "date",
    },
    {
        key: "sharing",
        type: "sharing",
    },
    {
        key: "username_and_slug",
        type: "link",
    },
    {
        key: "tags",
        type: "string",
    },
];

const gridConfig = computed(() => {
    return config[props.name];
})

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

onMounted(() => {
    getGridData();
});

async function executeOperation(operation: any, rowData: any) {
    const message = await operation.handler(rowData);
    if (message) {
        await getGridData();
        operationMessage.value = message;
    }
}
</script>

<template>
    <div>
        <BAlert v-if="!!operationMessage" variant="success" show>{{ operationMessage }}</BAlert>
        <BAlert v-if="!!errorMessage" variant="danger" show>{{ errorMessage }}</BAlert>
        <div>
            <h1 class="mb-3 h-lg">
                {{ gridConfig.title }}
            </h1>
            <table class="table table-striped">
                <thead>
                    <th v-for="(fieldEntry, fieldIndex) of fields" :key="fieldIndex">
                        {{ fieldEntry.title || fieldEntry.key }}
                    </th>
                </thead>
                <tr v-for="(rowData, rowIndex) of gridData" :key="rowIndex">
                    <td v-for="(fieldEntry, fieldIndex) of fields" :key="fieldIndex">
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
                    </td>
                </tr>
            </table>
        </div>
    </div>
</template>
