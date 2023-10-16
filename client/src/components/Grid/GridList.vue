<script setup lang="ts">
import axios from "axios";
import { BAlert } from "bootstrap-vue";
//@ts-ignore
import UtcDate from "components/UtcDate";
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { withPrefix } from "@/utils/redirect";

const router = useRouter();

interface Props {
    resource: string;
    title: string;
    url: string;
}

const props = withDefaults(defineProps<Props>(), {});

const gridData = ref();
const errorMessage = ref("");

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

async function getGridData() {
    try {
        const { data } = await axios.get(withPrefix(props.url));
        gridData.value = data;
        errorMessage.value = "";
    } catch (e) {
        errorMessage.value = "Failed to obtain grid data.";
    }
}

onMounted(() => {
    getGridData();
});
</script>

<template>
    <div>
        <BAlert v-if="!!errorMessage" variant="danger" show>{{ errorMessage }}</BAlert>
        <div>
            <h1 class="mb-3 h-lg">
                {{ title }}
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
                                    @click="operation.handler(rowData)">
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
