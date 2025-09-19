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
import { ref } from "vue";

import { GalaxyApi } from "@/api";
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

const getPage = async (id: string): Promise<PageData | undefined> => {
    const { data, error } = await GalaxyApi().GET("/api/pages/{id}", {
        params: {
            path: {
                id,
            },
        },
    });
    if (error) {
        rethrowSimple(error.err_msg);
    } else {
        return data as PageData;
    }
};

const loadPage = async () => {
    try {
        const data = await getPage(props.pageId);
        if (data) {
            publicUrl.value = `${getAppRoot()}u/${data.username}/p/${data.slug}`;
            content.value = data.content;
            contentFormat.value = data.content_format;
            contentData.value = data || {};
            title.value = data.title;
            loading.value = false;
        }
    } catch (error: any) {
        Toast.error(`Failed to load page: ${error}`);
    }
};

loadPage();
</script>
