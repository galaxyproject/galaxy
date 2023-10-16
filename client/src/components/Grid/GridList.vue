<script setup lang="ts">
import axios from "axios";
import { BAlert, BButton } from "bootstrap-vue";
import { computed, onMounted, ref, watch } from "vue";

import { withPrefix } from "@/utils/redirect";

interface Props {
    id: string;
    title: string;
    url: string;
}

const props = withDefaults(defineProps<Props>(), {
});

const gridData = ref();
const errorMessage = ref("");

const fields = [{
    key: "title",
    type: "string",
},
{
    key: "type",
    type: "string",
},
{
    key: "url",
    type: "string",
},
{
    key: "created",
    type: "string",
},
{
    key: "update_time",
    type: "string",
},
{
    key: "sharing",
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
                        <span v-if="fieldEntry.type == 'string'">
                            {{ rowData[fieldEntry.key] }}
                        </span>
                    </td>
                </tr>
            </table>
        </div>
    </div>
</template>
