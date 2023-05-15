<script setup lang="ts">
import LoadingSpan from "@/components/LoadingSpan.vue";
import DescribeObjectStore from "@/components/ObjectStore/DescribeObjectStore.vue";
import { getObjectStoreDetails } from "./services";
import { watch, ref } from "vue";
import type { ConcreteObjectStoreModel } from "./types";
import { errorMessageAsString } from "@/utils/simple-error";

interface ShowSelectObjectStoreProps {
    forWhat: string;
    preferredObjectStoreId: string;
}

const props = defineProps<ShowSelectObjectStoreProps>();

const objectStore = ref<ConcreteObjectStoreModel | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);

async function fetch() {
    loading.value = true;
    try {
        objectStore.value = await getObjectStoreDetails(props.preferredObjectStoreId);
    } catch (e) {
        error.value = errorMessageAsString(e);
    } finally {
        loading.value = false;
    }
}

watch(
    () => props.preferredObjectStoreId,
    async () => {
        fetch();
    }
);
fetch();
const loadingMessage = "Loading object store details";
</script>

<template>
    <div>
        <LoadingSpan v-if="loading" :message="loadingMessage | localize" />
        <DescribeObjectStore v-else-if="objectStore != null" :what="forWhat" :storage-info="objectStore">
        </DescribeObjectStore>
        <b-alert v-else-if="error" show variant="danger">{{ error }}</b-alert>
    </div>
</template>
