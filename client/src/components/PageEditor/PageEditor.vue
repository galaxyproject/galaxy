<template>
    <LoadingSpan v-if="loading" message="Loading Page" class="m-3" />
    <PageEditorMarkdown
        v-else
        :title="title"
        :page-id="pageId"
        :public-url="publicUrl"
        :content="content"
        :content-data="contentData" />
</template>

<script setup lang="ts">
import axios from "axios";
import { ref, watch } from "vue";

import { Toast } from "@/composables/toast";
import { getAppRoot } from "@/onload/loadConfig";
import { rethrowSimple } from "@/utils/simple-error";

import PageEditorMarkdown from "./PageEditorMarkdown.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface PageData {
    title: string;
    content: string;
    content_format: string;
    username: string;
    slug: string;
    [key: string]: any;
}

const props = defineProps<{
    pageId: string;
}>();

const title = ref("");
const content = ref<string>("");
const contentFormat = ref<string>("");
const contentData = ref<PageData>();
const publicUrl = ref<string>("");
const loading = ref(true);

const getPage = async (id: string): Promise<PageData> => {
    try {
        const { data } = await axios.get(`${getAppRoot()}api/pages/${id}`);
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
};

const loadPage = async () => {
    try {
        const data = await getPage(props.pageId);
        publicUrl.value = `${getAppRoot()}u/${data.username}/p/${data.slug}`;
        content.value = data.content;
        contentFormat.value = data.content_format;
        contentData.value = data || {};
        title.value = data.title;
        loading.value = false;
    } catch (error: any) {
        Toast.error(`Failed to load page: ${error}`);
    }
};

watch(() => props.pageId, loadPage);
</script>
