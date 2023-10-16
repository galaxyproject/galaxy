<script setup lang="ts">
/**
 * This component is strictly for backward compatibility. Tool developers should use the regular
 * data input field instead, which already allows the selection of library datasets and is more efficient.
 */
import axios from "axios";
import { BAlert, BButton } from "bootstrap-vue";
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
        return Array.isArray(props.value) ? props.value : [props.value];
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
            .map((x: OptionType) => ({ label: stripSlash(x.name), value: { id: x.id, name: stripSlash(x.name) } }));
        currentDataset.value = null;
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

function stripSlash(name: string) {
    return name.startsWith("/") ? name.substr(1) : name;
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
        <div v-if="currentDatasetOptions.length > 0" class="d-flex my-2">
            <FormSelect v-model="currentDataset" :options="currentDatasetOptions" />
            <BButton
                class="ml-2"
                data-description="form library add dataset"
                variant="link"
                @click="onAdd(currentDataset)">
                <icon icon="plus" />
            </BButton>
        </div>
        <div v-else v-localize class="text-muted mb-2">The selected library does not contain any datasets.</div>
        <div v-for="(v, vIndex) of valueAsArray" :key="vIndex">
            <span>
                <BButton
                    size="sm"
                    variant="link"
                    data-description="form library remove dataset"
                    @click="onRemove(v.id)">
                    <icon icon="trash" />
                </BButton>
                <span>{{ v.name }}</span>
            </span>
        </div>
    </div>
</template>
