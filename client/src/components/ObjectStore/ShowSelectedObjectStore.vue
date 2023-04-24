<script setup lang="ts">
import LoadingSpan from "@/components/LoadingSpan.vue";
import { ObjectStoreDetailsProvider } from "@/components/providers/ObjectStoreProvider";
import DescribeObjectStore from "@/components/ObjectStore/DescribeObjectStore.vue";

interface ShowSelectObjectStoreProps {
    forWhat: String;
    preferredObjectStoreId?: String | null;
}

withDefaults(defineProps<ShowSelectObjectStoreProps>(), {
    preferredObjectStoreId: null,
});

const loadingMessage = "Loading object store details";
</script>

<template>
    <ObjectStoreDetailsProvider
        :id="preferredObjectStoreId"
        v-slot="{ result: storageInfo, loading: isLoadingStorageInfo }">
        <LoadingSpan v-if="isLoadingStorageInfo" :message="loadingMessage | localize" />
        <DescribeObjectStore v-else :what="forWhat" :storage-info="storageInfo"> </DescribeObjectStore>
    </ObjectStoreDetailsProvider>
</template>
