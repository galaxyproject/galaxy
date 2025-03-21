<script setup lang="ts">
import { computed, ref, watch } from "vue";

import { type DatasetStorageDetails, GalaxyApi } from "@/api";
import { errorMessageAsString, rethrowSimple } from "@/utils/simple-error";

import RelocateLink from "./RelocateLink.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import DescribeObjectStore from "@/components/ObjectStore/DescribeObjectStore.vue";

interface DatasetStorageProps {
    datasetId: string;
    datasetType?: "hda" | "ldda";
    includeTitle?: boolean;
}

const props = withDefaults(defineProps<DatasetStorageProps>(), {
    datasetType: "hda",
    includeTitle: true,
});

const storageInfo = ref<DatasetStorageDetails | null>(null);
const errorMessage = ref<string | null>(null);

const discarded = computed(() => {
    return storageInfo.value?.dataset_state == "discarded";
});

const deferred = computed(() => {
    return storageInfo.value?.dataset_state == "deferred";
});

const sourceUri = computed(() => {
    const sources = storageInfo.value?.sources;
    if (!sources) {
        return null;
    }
    const rootSources = sources.filter((source) => !source.extra_files_path);
    if (rootSources.length == 0) {
        return null;
    }
    return rootSources[0]?.source_uri;
});

async function fetch() {
    const datasetId = props.datasetId;
    const datasetType = props.datasetType;
    try {
        const { data, error } = await GalaxyApi().GET("/api/datasets/{dataset_id}/storage", {
            params: {
                path: { dataset_id: datasetId },
                query: { hda_ldda: datasetType },
            },
        });
        if (error) {
            rethrowSimple(error);
        }
        storageInfo.value = data;
    } catch (error) {
        errorMessage.value = errorMessageAsString(error);
    }
}

watch(props, fetch, { immediate: true });
</script>

<template>
    <div>
        <h2 v-if="includeTitle" class="h-md">数据集存储</h2>
        <div v-if="errorMessage" class="error">{{ errorMessage }}</div>
        <LoadingSpan v-else-if="storageInfo == null"> </LoadingSpan>
        <div v-else-if="discarded">
            <p>该数据集已被丢弃，文件不可用于 Galaxy。</p>
        </div>
        <div v-else-if="deferred">
            <p>
                该数据集是远程的并且已延迟。数据集的文件不可用于 Galaxy。
                <span v-if="sourceUri">
                    当作业使用此数据集时，数据集将从 <b class="deferred-dataset-source-uri">{{ sourceUri }}</b> 下载。
                </span>
            </p>
        </div>
        <div v-else>
            <DescribeObjectStore what="该数据集存储在" :storage-info="storageInfo" />
        </div>
        <RelocateLink
            v-if="storageInfo"
            :dataset-id="datasetId"
            :dataset-storage-details="storageInfo"
            @relocated="fetch" />
    </div>
</template>