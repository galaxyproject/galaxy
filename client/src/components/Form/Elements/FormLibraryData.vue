<script setup lang="ts">
import axios from "axios";
import { computed, onMounted, ref, watch } from "vue";

import { withPrefix } from "@/utils/redirect";

import FormSelect from "./FormSelect.vue";

interface OptionType {
    id: string;
    name: string;
    type: string;
}

interface Props {
    id: string;
    multiple?: boolean;
    optional?: boolean;
    value?: Array<OptionType> | OptionType;
}

const props = withDefaults(defineProps<Props>(), {
    multiple: true,
    optional: false,
    value: null,
});

const currentDatasetOptions = ref([]);
const currentDataset = ref(null);
const currentLibraryOptions = ref([]);
const currentLibrary = ref(null);
const errorMessage = ref("");

const $emit = defineEmits(["input"]);

const valueAsArray = computed(() => {
    if (props.value) {
        if (Array.isArray(props.value)) {
            return props.value;
        } else {
            return [props.value];
        }
    } else {
        return [];
    }
});

async function getDatasetList() {
    try {
        const datasetUrl = `api/libraries/${currentLibrary.value}/contents`;
        const { data } = await axios.get(withPrefix(datasetUrl));
        currentDatasetOptions.value = data
            .filter((x: OptionType) => x.type === "file")
            .map((x: OptionType) => ({ label: x.name, value: { id: x.id, name: x.name } }));
        errorMessage.value = "";
    } catch (e) {
        errorMessage.value = "Failed to access library contents.";
    }
}

async function getLibraryList() {
    try {
        const { data } = await axios.get(withPrefix("api/libraries?deleted=false"));
        currentLibraryOptions.value = data.map((x: OptionType) => ({ label: x.name, value: x.id }));
        errorMessage.value = "";
    } catch (e) {
        errorMessage.value = "Failed to access library list.";
    }
}

function onAdd(newDataset: OptionType) {
    if (newDataset) {
        if (props.multiple) {
            const newDatasetArray = valueAsArray.value;
            const isNewDataset = newDatasetArray.findIndex((x) => x.id === newDataset.id) === -1;
            if (isNewDataset) {
                newDatasetArray.push(newDataset);
                $emit("input", newDatasetArray);
            }
        } else {
            $emit("input", newDataset);
        }
    }
}

function onRemove(datasetId: string) {
    const newValue = valueAsArray.value.filter((x) => x.id !== datasetId);
    if (newValue.length > 0) {
        $emit("input", newValue);
    } else {
        $emit("input", null);
    }
}

onMounted(() => {
    getLibraryList();
});

watch(currentLibrary, () => {
    getDatasetList();
});
</script>

<template>
    <div>
        <BAlert v-if="!!errorMessage" variant="danger" show>{{ errorMessage }}</BAlert>
        <FormSelect v-model="currentLibrary" :options="currentLibraryOptions" />
        <div class="d-flex my-2">
            <FormSelect v-model="currentDataset" :optional="true" :options="currentDatasetOptions" />
            <BButton v-if="currentDataset" class="ml-2" variant="link" @click="onAdd(currentDataset)"
                ><icon icon="plus"
            /></BButton>
        </div>
        <div v-for="(v, vIndex) of valueAsArray" :key="vIndex">
            <span>
                <BButton size="sm" variant="link" @click="onRemove(v.id)">
                    <icon icon="trash" />
                </BButton>
                <span>{{ v.name }}</span>
            </span>
        </div>
    </div>
</template>
