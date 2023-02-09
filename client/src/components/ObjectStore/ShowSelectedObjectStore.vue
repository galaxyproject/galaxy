<template>
    <ObjectStoreDetailsProvider
        :id="preferredObjectStoreId"
        v-slot="{ result: storageInfo, loading: isLoadingStorageInfo }">
        <LoadingSpan v-if="isLoadingStorageInfo" :message="loadingMessage | localize" />
        <DescribeObjectStore v-else :what="forWhat" :storage-info="storageInfo"> </DescribeObjectStore>
    </ObjectStoreDetailsProvider>
</template>

<script>
import LoadingSpan from "components/LoadingSpan";
import { ObjectStoreDetailsProvider } from "components/providers/ObjectStoreProvider";
import DescribeObjectStore from "components/ObjectStore/DescribeObjectStore";

export default {
    components: {
        DescribeObjectStore,
        LoadingSpan,
        ObjectStoreDetailsProvider,
    },
    props: {
        forWhat: {
            type: String,
            required: true,
        },
        preferredObjectStoreId: {
            type: String,
            default: null,
        },
    },
    data() {
        return {
            loadingMessage: "Loading object store details",
        };
    },
};
</script>
