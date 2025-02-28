<template>
    <b-card body-class="p-0">
        <b-card-header>
            <span class="float-right">
                <b-button
                    v-b-tooltip.hover
                    :href="downloadUrl"
                    variant="link"
                    size="sm"
                    role="button"
                    title="Download Collection"
                    type="button"
                    class="py-0 px-1">
                    <span class="fa fa-download" />
                </b-button>
                <b-button
                    v-if="currentUser && currentHistoryId"
                    v-b-tooltip.hover
                    href="#"
                    role="button"
                    variant="link"
                    title="Import Collection"
                    type="button"
                    class="py-0 px-1"
                    @click="onCopyCollection(currentHistoryId)">
                    <span class="fa fa-file-import" />
                </b-button>
            </span>
            <span>
                <span>Dataset Collection:</span>
                <span class="font-weight-light">{{ itemName }}</span>
            </span>
        </b-card-header>
        <b-card-body>
            <LoadingSpan v-if="loading" message="Loading Collection" />
            <div v-else class="content-height">
                <b-alert v-if="!!messageText" :variant="messageVariant" show>
                    {{ messageText }}
                </b-alert>
                <CollectionTree :node="itemContent" :skip-head="true" />
            </div>
        </b-card-body>
    </b-card>
</template>

<script setup lang="ts">
import axios from "axios";
import { computed, ref, watch } from "vue";

import { copyCollection } from "@/components/Markdown/services";
import { getAppRoot } from "@/onload/loadConfig";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";

import CollectionTree from "./CollectionTree.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const props = defineProps<{
    collectionId: string;
}>();

const userStore = useUserStore();
const historyStore = useHistoryStore();

const currentUser = computed(() => userStore.currentUser);
const currentHistoryId = computed(() => historyStore.currentHistoryId);

const itemContent = ref<any>(null);
const loading = ref(true);
const messageText = ref<string>("");
const messageVariant = ref<string>("");

const itemName = computed(() => itemContent.value?.name || "");
const itemUrl = computed(() => `${getAppRoot()}api/dataset_collections/${props.collectionId}`);
const downloadUrl = computed(() => `${getAppRoot()}api/dataset_collections/${props.collectionId}/download`);

const onCopyCollection = async (currentHistoryId: string) => {
    try {
        await copyCollection(props.collectionId, currentHistoryId);
        messageVariant.value = "success";
        messageText.value = "Successfully copied to current history.";
    } catch (error) {
        messageVariant.value = "danger";
        messageText.value = error as string;
    }
};

const getContent = async () => {
    try {
        const response = await axios.get(itemUrl.value);
        itemContent.value = response.data;
    } catch (e) {
        messageVariant.value = "danger";
        messageText.value = `Failed to retrieve content. ${e}`;
    } finally {
        loading.value = false;
    }
};

watch(
    () => props.collectionId,
    () => getContent(),
    { immediate: true }
);
</script>

<style scoped>
.content-height {
    max-height: 15rem;
    overflow-y: auto;
}
</style>
