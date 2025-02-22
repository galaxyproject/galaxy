<template>
    <div class="my-4">
        <b-alert v-if="errorMessage" variant="danger" show>{{ errorMessage }}</b-alert>
        <div v-else>
            <label class="form-label font-weight-bold">Select a {{ type }}:</label>
            <Multiselect v-model="currentValue" label="name" :options="options" @search-change="search" />
        </div>
    </div>
</template>

<script setup lang="ts">
import { debounce } from "lodash";
import { computed, type Ref, ref } from "vue";
import Multiselect from "vue-multiselect";

import { GalaxyApi } from "@/api";

import type { ApiResponse, OptionType } from "./types";

const DELAY = 300;

const props = defineProps<{
    type: "dataset" | "workflow";
    objectId?: string;
}>();

const emit = defineEmits<{
    (e: "change", newValue: OptionType): void;
}>();

const errorMessage = ref("");
const objectName = ref("...");
const options: Ref<Array<OptionType>> = ref([]);

const currentValue = computed({
    get: () => ({
        id: props.objectId,
        name: objectName.value,
    }),
    set: (newValue: OptionType) => {
        emit("change", newValue);
    },
});

const search = debounce(async (query: string = "") => {
    if (!errorMessage.value) {
        const { data, error } = await doQuery(query);
        if (error) {
            errorMessage.value = error.err_msg;
        } else {
            errorMessage.value = "";
            if (data) {
                options.value = data.map((d) => ({ id: d.id, name: d.name }));
            } else {
                options.value = [];
            }
        }
    }
}, DELAY);

async function doQuery(query: string = ""): Promise<ApiResponse> {
    if (props.type === "workflow") {
        return getWorkflow(query);
    } else {
        return getDataset(query);
    }
}

async function getDataset(query: string = ""): Promise<ApiResponse> {
    const { data, error } = await GalaxyApi().GET("/api/datasets", {
        params: {
            query: {
                q: ["name-contains"],
                qv: [query],
                offset: 0,
                limit: 50,
            },
        },
    });
    return { data, error };
}

async function getWorkflow(query: string = ""): Promise<ApiResponse> {
    const { data, error } = await GalaxyApi().GET("/api/workflows");
    return { data, error };
}

search();
</script>
