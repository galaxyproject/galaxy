<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router/composables";

import { GalaxyApi } from "@/api";
import { useObjectStoreStore } from "@/stores/objectStoreStore";
import localize from "@/utils/localization";
import { rethrowSimple } from "@/utils/simple-error";

import type { DataValuePoint } from "./Charts";
import { byteFormattingForChart, useDataLoading } from "./util";

import BarChart from "./Charts/BarChart.vue";
import ObjectStoreActions from "./ObjectStoreActions.vue";
import OverviewPage from "./OverviewPage.vue";
import ShowObjectStore from "./ShowObjectStore.vue";
import WarnDeletedHistories from "./WarnDeletedHistories.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const router = useRouter();

const objectStoresBySizeData = ref<DataValuePoint[] | null>(null);

const { getObjectStoreNameById } = useObjectStoreStore();

const { isLoading, loadDataOnMount } = useDataLoading();

loadDataOnMount(async () => {
    const { data, error } = await GalaxyApi().GET("/api/users/{user_id}/objectstore_usage", {
        params: { path: { user_id: "current" } },
    });

    if (error) {
        rethrowSimple(error);
        return;
    }

    const objectStoresBySize = data.sort((a, b) => b.total_disk_usage - a.total_disk_usage);
    objectStoresBySizeData.value = objectStoresBySize.map((objectStore) => ({
        id: objectStore.object_store_id,
        label: getObjectStoreNameById(objectStore.object_store_id) ?? objectStore.object_store_id,
        value: objectStore.total_disk_usage,
    }));
});

function onViewObjectStore(objectStoreId: string) {
    router.push({ name: "ObjectStoreOverview", params: { objectStoreId } });
}
</script>
<template>
    <OverviewPage title="按位置存储概览">
        <p class="text-justify">
            在这里，您可以找到各种图表，显示所有历史记录按物理存储位置分组的存储大小。
        </p>
        <WarnDeletedHistories />
        <div v-if="isLoading" class="text-center">
            <LoadingSpan class="mt-5" :message="localize('正在加载您的存储数据。这可能需要一些时间...')" />
        </div>
        <div v-else>
            <BarChart
                v-if="objectStoresBySizeData"
                :description="
                    localize(
                        `此图表显示您的Galaxy数据是如何按存储位置分类存储的。点击柱状图可查看有关该存储位置的更多信息。`
                    )
                "
                :data="objectStoresBySizeData"
                :enable-selection="true"
                v-bind="byteFormattingForChart">
                <template v-slot:title>
                    <b>{{ localize(`按使用量排列的存储位置`) }}</b>
                </template>
                <template v-slot:tooltip="{ data }">
                    <ShowObjectStore v-if="data" :object-store-id="data.id" />
                </template>
                <template v-slot:selection="{ data }">
                    <ObjectStoreActions :data="data" @view-item="onViewObjectStore" />
                </template>
            </BarChart>
        </div>
    </OverviewPage>
</template>
