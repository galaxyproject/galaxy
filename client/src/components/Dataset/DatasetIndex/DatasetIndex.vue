<script setup lang="ts">
import { computed } from "vue";

import type { DatasetExtraFiles } from "@/api/datasets";
import { type PathDestination, useDatasetPathDestination } from "@/composables/datasetPathDestination";

interface Props {
    historyDatasetId: string;
    path?: string;
}

const { datasetPathDestination } = useDatasetPathDestination();

const props = defineProps<Props>();

const pathDestination = computed<PathDestination | null>(() =>
    datasetPathDestination.value(props.historyDatasetId, props.path)
);

const directoryContent = computed(() => {
    if (!pathDestination.value) {
        return;
    }

    if (pathDestination.value.fileLink) {
        return;
    }

    if (pathDestination.value.isDirectory) {
        return removeParentDirectory(pathDestination.value.datasetContent, pathDestination.value.filepath);
    } else if (props.path === undefined || props.path === "undefined") {
        return pathDestination.value.datasetContent;
    }
    return pathDestination.value.datasetContent;
});

const errorMessage = computed(() => {
    if (!pathDestination.value) {
        return `数据集不是复合型的!`;
    }

    if (pathDestination.value.fileLink) {
        return `不是目录!`;
    }

    if (pathDestination.value.isDirectory) {
        return undefined;
    } else if (props.path === undefined || props.path === "undefined") {
        return undefined;
    } else {
        return `未找到!`;
    }
});

function removeParentDirectory(datasetContent: DatasetExtraFiles, filepath?: string) {
    return datasetContent.filter((entry) => {
        if (entry.path.startsWith(`${filepath}/`)) {
            entry.path = entry.path.replace(`${filepath}/`, "");
            return entry;
        }
    });
}

const fields = [
    {
        key: "path",
        sortable: true,
    },
    {
        key: "class",
        label: "类型",
        sortable: true,
    },
];
</script>

<template>
    <div>
        <b-table
            v-if="directoryContent && !errorMessage"
            thead-class="hidden_header"
            striped
            hover
            :fields="fields"
            :items="directoryContent">
        </b-table>
        <div v-if="errorMessage">
            <b v-if="path">{{ path }}</b> {{ errorMessage }}
        </div>
    </div>
</template>
