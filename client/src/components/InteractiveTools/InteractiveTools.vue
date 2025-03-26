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
            :items="activeInteractiveTools"
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
                    <FontAwesomeIcon :icon="['fas', 'stop-circle']" />
                </b-button>
            </template>
            <template v-slot:cell(name)="row">
                <a
                    :id="createId('link', row.item.id)"
                    v-b-tooltip
                    title="Open Interactive Tool"
                    :index="row.index"
                    :href="row.item.target"
                    target="_blank"
                    :name="row.item.name"
                    >{{ row.item.name }}
                    <FontAwesomeIcon :icon="['fas', 'external-link-alt']" />
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

<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faExternalLinkAlt, faStopCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, onMounted, ref } from "vue";

import { getAppRoot } from "@/onload/loadConfig";
import { useEntryPointStore } from "@/stores/entryPointStore";

import { Services } from "./services";

import UtcDate from "@/components/UtcDate.vue";

library.add(faExternalLinkAlt, faStopCircle);

const error = ref<Error | null>(null);
const filter = ref("");
const messages = ref<string[]>([]);
const nInteractiveTools = ref(0);
const root = ref("");
const services = ref<Services | null>(null);

const entryPointStore = useEntryPointStore();
const activeInteractiveTools = computed(() => entryPointStore.entryPoints);

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
    return activeInteractiveTools.value.length === 0;
});

const load = () => {
    filter.value = "";
};

const filtered = (items: any[]) => {
    nInteractiveTools.value = items.length;
};

const stopInteractiveTool = (toolId: string, toolName: string) => {
    services.value
        ?.stopInteractiveTool(toolId)
        .then(() => {
            entryPointStore.removeEntryPoint(toolId);
        })
        .catch((error: Error) => {
            messages.value.push(`Failed to stop interactive tool ${toolName}: ${error.message}`);
        });
};

const createId = (tagLabel: string, id: string): string => {
    return tagLabel + "-" + id;
};

onMounted(() => {
    root.value = getAppRoot();
    services.value = new Services({ root: root.value });
    load();
});
</script>
