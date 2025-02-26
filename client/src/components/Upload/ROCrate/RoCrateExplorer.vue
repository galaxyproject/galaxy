<script setup lang="ts">
import { ref } from "vue";

import { type ROCrateFile, type ROCrateSummary } from "./rocrate.utils";

import ExternalLink from "@/components/ExternalLink.vue";
import UtcDate from "@/components/UtcDate.vue";

interface Props {
    crateSummary: ROCrateSummary;
    selectedItems: ROCrateFile[];
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "update:selectedItems", value: ROCrateFile[]): void;
}>();

const localSelectedItems = ref<ROCrateFile[]>(props.selectedItems);

function toggleSelection(item: ROCrateFile) {
    const index = localSelectedItems.value.findIndex((selected) => selected.id === item.id);
    if (index === -1) {
        localSelectedItems.value.push(item);
    } else {
        localSelectedItems.value.splice(index, 1);
    }
    emit("update:selectedItems", localSelectedItems.value);
}
</script>

<template>
    <div class="rocrate-explorer">
        <h2>RO-Crate Summary</h2>

        <div>
            <strong>Publication Date:</strong>
            <UtcDate :date="props.crateSummary.publicationDate.toISOString()" mode="pretty" />
            (<UtcDate :date="props.crateSummary.publicationDate.toISOString()" mode="elapsed" />)
        </div>

        <strong>License:</strong> {{ props.crateSummary.license }}

        <div v-if="props.crateSummary.creators.length > 0">
            <strong>Creators</strong>
            <ul>
                <li v-for="creator in props.crateSummary.creators" :key="creator.id">
                    {{ creator.name }}
                </li>
            </ul>
        </div>

        <h3>Contents</h3>

        <div v-if="props.crateSummary.workflows.length > 0">
            <strong>Workflows</strong>
            <ul>
                <li v-for="workflow in props.crateSummary.workflows" :key="workflow.id">
                    <input type="checkbox" :value="workflow" @change="toggleSelection(workflow)" />
                    {{ workflow.name }}
                </li>
            </ul>
        </div>

        <div v-if="props.crateSummary.datasets.length > 0">
            <strong>Datasets</strong>
            <ul>
                <li v-for="dataset in props.crateSummary.datasets" :key="dataset.id">
                    <input type="checkbox" :value="dataset" @change="toggleSelection(dataset)" />
                    {{ dataset.name }} (Type: {{ dataset.type }})
                </li>
            </ul>
        </div>

        <div v-if="props.crateSummary.conformsTo.length > 0">
            <strong>Conforms To</strong>
            <ul>
                <li v-for="conform in props.crateSummary.conformsTo" :key="conform.id">
                    <ExternalLink :href="conform.id"> {{ conform.name }} {{ conform.version }} </ExternalLink>
                </li>
            </ul>
        </div>
    </div>
</template>
