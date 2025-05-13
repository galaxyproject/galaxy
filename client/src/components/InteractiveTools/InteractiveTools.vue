<script setup lang="ts">
import { faExternalLinkAlt, faStop } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { useInteractiveToolsStore } from "@/stores/interactiveToolsStore";

import UtcDate from "@/components/UtcDate.vue";

const filter = ref("");
const nInteractiveTools = ref(0);
const router = useRouter();

// Use the stores
const interactiveToolsStore = useInteractiveToolsStore();

// Get reactive refs from stores
const { messages, activeTools } = storeToRefs(interactiveToolsStore);

const fields = [
    {
        label: "",
        key: "actions",
        class: "text-center",
    },
    {
        label: "Name",
        key: "name",
        sortable: true,
    },
    {
        label: "Job Info",
        key: "job_info",
        sortable: true,
    },
    {
        label: "Created",
        key: "created_time",
        sortable: true,
    },
    {
        label: "Last Updated",
        key: "last_updated",
        sortable: true,
    },
];

const showNotFound = computed(() => {
    return nInteractiveTools.value === 0 && filter.value !== "" && !isActiveToolsListEmpty.value;
});

const isActiveToolsListEmpty = computed(() => {
    return activeTools.value.length === 0;
});

const load = () => {
    filter.value = "";
};

const filtered = (items: any[]) => {
    nInteractiveTools.value = items.length;
};

const stopInteractiveTool = (toolId: string, toolName: string) => {
    interactiveToolsStore.stopInteractiveTool(toolId, toolName);
};

const createId = (tagLabel: string, id: string): string => {
    return tagLabel + "-" + id;
};

const openInteractiveTool = (toolId: string) => {
    router.push(`/interactivetool_entry_points/${toolId}/display`);
};

onMounted(() => {
    interactiveToolsStore.getActiveTools();
    load();
});
</script>
<template>
    <div aria-labelledby="interactive-tools-heading">
        <b-alert v-for="(message, index) in messages" :key="index" :show="3" variant="danger">{{ message }}</b-alert>
        <h1 id="interactive-tools-heading" class="h-lg">Active Interactive Tools</h1>
        <b-row class="mb-3">
            <b-col cols="6">
                <b-input
                    id="interactivetool-search"
                    v-model="filter"
                    class="m-1"
                    name="query"
                    placeholder="Search Interactive Tool"
                    autocomplete="off"
                    type="text" />
            </b-col>
        </b-row>
        <b-table
            id="interactive-tool-table"
            striped
            :fields="fields"
            :items="activeTools"
            :filter="filter"
            @filtered="filtered">
            <template v-slot:cell(actions)="row">
                <b-button
                    :id="createId('stop', row.item.id)"
                    v-b-tooltip.hover
                    variant="link"
                    class="p-0"
                    title="Stop this interactive tool"
                    @click.stop="stopInteractiveTool(row.item.id, row.item.name)">
                    <FontAwesomeIcon :icon="faStop" />
                </b-button>
            </template>
            <template v-slot:cell(name)="row">
                <a
                    :id="createId('link', row.item.id)"
                    v-b-tooltip
                    title="Open Interactive Tool"
                    :index="row.index"
                    href="#"
                    :name="row.item.name"
                    @click.prevent="openInteractiveTool(row.item.id)"
                    >{{ row.item.name }}
                    <FontAwesomeIcon :icon="faExternalLinkAlt" />
                </a>
                <!-- Add a direct link option as well -->
                <a
                    :id="createId('external-link', row.item.id)"
                    v-b-tooltip
                    class="ml-2"
                    title="Open in new tab"
                    :href="row.item.target"
                    target="_blank">
                    <small>(new tab)</small>
                </a>
            </template>
            <template v-slot:cell(job_info)="row">
                <label v-if="row.item.active"> running </label>
                <label v-else> stopped </label>
            </template>
            <template v-slot:cell(created_time)="row">
                <UtcDate :date="row.item.created_time" mode="elapsed" />
            </template>
            <template v-slot:cell(last_updated)="row">
                <UtcDate :date="row.item.modified_time" mode="elapsed" />
            </template>
        </b-table>
        <label v-if="isActiveToolsListEmpty">You do not have active interactive tools yet </label>
        <div v-if="showNotFound">
            No matching entries found for: <span class="font-weight-bold">{{ filter }}</span
            >.
        </div>
    </div>
</template>
