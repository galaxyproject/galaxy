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
                    title="下载集合"
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
                    title="导入集合"
                    type="button"
                    class="py-0 px-1"
                    @click="onCopyCollection(currentHistoryId)">
                    <span class="fa fa-file-import" />
                </b-button>
            </span>
            <span>
                <span>数据集合：</span>
                <span class="font-weight-light">{{ itemName }}</span>
            </span>
        </b-card-header>
        <b-card-body>
            <LoadingSpan v-if="loading" message="正在加载集合" />
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
import { computed, ref, watch } from "vue";

import { GalaxyApi } from "@/api";
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
const downloadUrl = computed(() => `${getAppRoot()}api/dataset_collections/${props.collectionId}/download`);

const onCopyCollection = async (currentHistoryId: string) => {
    try {
        await copyCollection(props.collectionId, currentHistoryId);
        messageVariant.value = "success";
        messageText.value = "已成功复制到当前历史记录。";
    } catch (error) {
        messageVariant.value = "danger";
        messageText.value = error as string;
    }
};

const getContent = async () => {
    const { data, error } = await GalaxyApi().GET("/api/dataset_collections/{id}", {
        params: {
            path: { id: props.collectionId },
        },
    });
    if (error) {
        messageVariant.value = "danger";
        messageText.value = `获取内容失败。${error}`;
    } else {
        messageText.value = "";
    }
    itemContent.value = data;
    loading.value = false;
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
