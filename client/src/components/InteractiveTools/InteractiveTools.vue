<script setup lang="ts">
import { faExternalLinkAlt, faStop } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BFormInput } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import type { TableField } from "@/components/Common/GTable.types";
import { useInteractiveToolsStore } from "@/stores/interactiveToolsStore";

import GLink from "@/components/BaseComponents/GLink.vue";
import GTable from "@/components/Common/GTable.vue";
import Heading from "@/components/Common/Heading.vue";
import UtcDate from "@/components/UtcDate.vue";

interface InteractiveToolRow {
    id: string;
    name: string;
    active: boolean;
    created_time: string;
    modified_time: string;
    target?: string;
    job_info: string;
}

const filter = ref("");
const router = useRouter();

// Use the stores
const interactiveToolsStore = useInteractiveToolsStore();

// Get reactive refs from stores
const { messages, activeTools } = storeToRefs(interactiveToolsStore);

const fields: TableField[] = [
    {
        key: "actions",
        label: "",
        align: "center",
    },
    {
        key: "name",
        label: "Name",
        sortable: true,
    },
    {
        key: "job_info",
        label: "Job Info",
        sortable: true,
    },
    {
        key: "created_time",
        label: "Created",
        sortable: true,
    },
    {
        key: "modified_time",
        label: "Last Updated",
        sortable: true,
    },
];

const tableItems = computed<InteractiveToolRow[]>(() => {
    return activeTools.value.map((tool) => ({
        ...tool,
        job_info: tool.active ? "Running" : "Starting",
    }));
});

const filteredTools = computed<InteractiveToolRow[]>(() => {
    const query = filter.value.trim().toLowerCase();
    if (!query) {
        return tableItems.value;
    }

    return tableItems.value.filter((tool) => {
        return [tool.name, tool.job_info, tool.created_time, tool.modified_time, tool.target]
            .filter((value): value is string => Boolean(value))
            .some((value) => value.toLowerCase().includes(query));
    });
});

const showNotFound = computed(() => {
    return filteredTools.value.length === 0 && filter.value !== "" && !isActiveToolsListEmpty.value;
});

const isActiveToolsListEmpty = computed(() => {
    return activeTools.value.length === 0;
});

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
    filter.value = "";
});
</script>

<template>
    <div aria-labelledby="interactive-tools-heading">
        <BAlert v-for="(message, index) in messages" :key="index" :show="3" variant="danger">
            {{ message }}
        </BAlert>

        <Heading id="interactive-tools-heading" h1 separator inline size="lg"> Active Interactive Tools </Heading>

        <BFormInput
            id="interactivetool-search"
            v-model="filter"
            class="m-1"
            name="query"
            placeholder="Search Interactive Tool"
            autocomplete="off"
            type="text" />

        <GTable id="interactive-tool-table" show-empty striped :fields="fields" :items="filteredTools">
            <template v-slot:empty>
                <BAlert variant="info" show class="mb-0">
                    <div v-if="isActiveToolsListEmpty">You do not have active interactive tools yet</div>
                    <div v-else-if="showNotFound">
                        No matching entries found for:
                        <span class="font-weight-bold"> {{ filter }} </span>.
                    </div>
                </BAlert>
            </template>

            <template v-slot:cell(actions)="{ item }">
                <BButton
                    :id="createId('stop', item.id)"
                    v-g-tooltip.hover
                    variant="link"
                    class="p-0"
                    title="Stop this interactive tool"
                    @click.stop="stopInteractiveTool(item.id, item.name)">
                    <FontAwesomeIcon :icon="faStop" />
                </BButton>
            </template>

            <template v-slot:cell(name)="{ item, index }">
                <GLink
                    :id="createId('link', item.id)"
                    tooltip
                    title="Open Interactive Tool"
                    :index="index"
                    :name="item.name"
                    @click.prevent="openInteractiveTool(item.id)">
                    {{ item.name }}
                </GLink>

                <GLink
                    v-if="item.target"
                    :id="createId('external-link', item.id)"
                    tooltip
                    class="ml-2"
                    target="_blank"
                    title="Open in new tab"
                    :href="item.target">
                    <FontAwesomeIcon :icon="faExternalLinkAlt" />
                </GLink>
            </template>

            <template v-slot:cell(job_info)="{ item }">
                <span v-if="item.active"> Running </span>
                <span v-else> Starting </span>
            </template>

            <template v-slot:cell(created_time)="{ item }">
                <UtcDate :date="item.created_time" mode="elapsed" />
            </template>

            <template v-slot:cell(modified_time)="{ item }">
                <UtcDate :date="item.modified_time" mode="elapsed" />
            </template>
        </GTable>
    </div>
</template>
