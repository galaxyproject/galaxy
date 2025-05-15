<script setup lang="ts">
import { ref, watch } from "vue";

import { getObjectStoreDetails } from "@/api/objectStores";
import localize from "@/utils/localization";
import { errorMessageAsString } from "@/utils/simple-error";

import type { ConcreteObjectStoreModel } from "./types";

import LoadingSpan from "@/components/LoadingSpan.vue";
import DescribeObjectStore from "@/components/ObjectStore/DescribeObjectStore.vue";

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
const loadingMessage = localize("Loading storage location details");
</script>

<template>
    <div>
        <LoadingSpan v-if="loading" :message="loadingMessage" />
        <DescribeObjectStore v-else-if="objectStore != null" :what="forWhat" :storage-info="objectStore">
        </DescribeObjectStore>
        <b-alert v-else-if="error" show variant="danger">{{ error }}</b-alert>
    </div>
</template>
