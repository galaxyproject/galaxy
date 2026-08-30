<script setup lang="ts">
import { ref, watch } from "vue";

import { getObjectStoreDetails } from "@/api/objectStores";
import type { ConcreteObjectStoreModel } from "@/components/ObjectStore/types";
import { errorMessageAsString } from "@/utils/simple-error";

import GAlert from "@/components/BaseComponents/GAlert.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import DescribeObjectStore from "@/components/ObjectStore/DescribeObjectStore.vue";

interface Props {
    objectStoreId: string;
}

const props = defineProps<Props>();

const objectStore = ref<ConcreteObjectStoreModel | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);

async function fetch() {
    loading.value = true;
    try {
        objectStore.value = await getObjectStoreDetails(props.objectStoreId);
    } catch (e) {
        error.value = errorMessageAsString(e);
    } finally {
        loading.value = false;
    }
}

watch(
    () => props.objectStoreId,
    async () => {
        fetch();
    },
);
fetch();
const loadingMessage = "Loading Galaxy storage details";
const forWhat = "This Galaxy storage is";
</script>

<template>
    <div style="width: 300px">
        <LoadingSpan v-if="loading" v-localize :message="loadingMessage" />
        <DescribeObjectStore v-else-if="objectStore != null" :what="forWhat" :storage-info="objectStore">
        </DescribeObjectStore>
        <GAlert v-else-if="error" show variant="danger">{{ error }}</GAlert>
    </div>
</template>
