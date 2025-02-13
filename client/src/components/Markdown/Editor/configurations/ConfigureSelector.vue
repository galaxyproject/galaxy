<template>
    <div class="my-4">
        <b-alert v-if="errorMessage" variant="danger" show>{{ errorMessage }}</b-alert>
        <div v-else>
            <label class="form-label">Select a dataset:</label>
            <Multiselect v-model="currentValue" label="name" :options="options" @search-change="search" />
        </div>
    </div>
</template>

<script setup lang="ts">
import { debounce } from "lodash";
import { computed, type Ref, ref } from "vue";
import Multiselect from "vue-multiselect";

import { GalaxyApi } from "@/api";

const DELAY = 300;

interface OptionType {
    id: string | null | undefined;
    name: string | null | undefined;
}

interface ContentType {
    dataset_id: string;
    dataset_name?: string;
}

const props = defineProps<{
    contentObject: ContentType;
}>();

const emit = defineEmits<{
    (e: "change", content: OptionType): void;
}>();

const errorMessage = ref("");
const options: Ref<Array<OptionType>> = ref([]);

const currentValue = computed({
    get: () => ({
        id: props.contentObject?.dataset_id,
        name: props.contentObject?.dataset_name || props.contentObject?.dataset_id,
    }),
    set: (newValue: OptionType) => {
        emit("change", newValue);
    },
});

const search = debounce(async (query: string = "") => {
    if (!errorMessage.value) {
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
        if (error) {
            errorMessage.value = error.err_msg;
        } else {
            errorMessage.value = "";
            options.value = data.map((d) => ({ id: d.id, name: d.name }));
        }
    }
}, DELAY);

search();
</script>
