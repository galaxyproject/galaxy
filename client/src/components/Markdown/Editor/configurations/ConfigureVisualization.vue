<template>
    <div class="my-4">
        <b-alert v-if="errorMessage" variant="danger" show>{{ errorMessage }}</b-alert>
        <label class="form-label">Select a visualization dataset:</label>
        <Multiselect v-model="currentValue" label="name" :options="options" @search-change="search" />
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

const props = defineProps<{
    content: string;
}>();

const emit = defineEmits<{
    (e: "change", content: string): void;
}>();

const errorMessage = ref("");
const options: Ref<Array<OptionType>> = ref([]);

const currentContent = computed(() => JSON.parse(props.content));
const currentValue = computed({
    get: () => ({
        id: currentContent.value?.dataset_id,
        name: currentContent.value?.dataset_id,
    }),
    set: (newValue) => {
        const newValues = { ...currentContent.value, dataset_id: newValue.id };
        emit("change", JSON.stringify(newValues, null, 4));
    },
});

const search = debounce(async (query: string = "") => {
    const { data, error } = await GalaxyApi().GET("/api/datasets", {
        params: {
            query: {
                q: ["name-contains"],
                qv: [query],
                offset: 0,
                limit: 100,
            },
        },
    });
    if (error) {
        errorMessage.value = error.err_msg;
    } else {
        errorMessage.value = "";
        options.value = data.map((d) => ({ id: d.id, name: d.name }));
    }
}, DELAY);

search();
</script>
