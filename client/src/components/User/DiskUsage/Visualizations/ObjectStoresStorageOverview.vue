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
    <OverviewPage title="Storage overview by location">
        <p class="text-justify">
            Here you can find various graphs displaying the storage size taken by all your histories grouped by where
            they are physically stored.
        </p>
        <WarnDeletedHistories />
        <div v-if="isLoading" class="text-center">
            <LoadingSpan class="mt-5" :message="localize('Loading your storage data. This may take a while...')" />
        </div>
        <div v-else>
            <BarChart
                v-if="objectStoresBySizeData"
                :description="
                    localize(
                        `This graph displays how your Galaxy data is stored sorted into the location is stored in. Click on a bar to see more information about the Galaxy storage.`
                    )
                "
                :data="objectStoresBySizeData"
                :enable-selection="true"
                v-bind="byteFormattingForChart">
                <template v-slot:title>
                    <b>{{ localize(`Galaxy Storage by Usage`) }}</b>
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
