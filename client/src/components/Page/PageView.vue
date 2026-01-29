<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, onMounted, ref } from "vue";

import type { PublishedItem as PublishedItemType } from "@/components/Common/models/PublishedItem";
import { useConfig } from "@/composables/config";
import { useUserStore } from "@/stores/userStore";
import { urlData } from "@/utils/url";

import Heading from "@/components/Common/Heading.vue";
import PublishedItem from "@/components/Common/PublishedItem.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import Markdown from "@/components/Markdown/Markdown.vue";
import PageHtml from "@/components/PageDisplay/PageHtml.vue";

interface PageData extends PublishedItemType {
    id: string;
    content: string;
    content_format: string;
    slug: string;
}

interface Props {
    pageId: string;
    embed?: boolean;
    showHeading?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    embed: false,
    showHeading: true,
});

const { config, isConfigLoaded } = useConfig(true);
const userStore = useUserStore();
const { currentUser } = storeToRefs(userStore);

const page = ref<PageData>();
const loading = ref(true);
const errorMessage = ref("");

const hasError = computed(() => !!errorMessage.value);
const dataUrl = computed(() => `/api/pages/${props.pageId}`);
const exportUrl = computed(() => `${dataUrl.value}.pdf`);
const userOwnsPage = computed(() => {
    if (!currentUser.value || !page.value) {
        return false;
    }
    // Check if the user is anonymous first
    if ("isAnonymous" in currentUser.value && currentUser.value.isAnonymous) {
        return false;
    }
    // Check username if available
    return currentUser.value.username === page.value.username;
});

async function load() {
    loading.value = true;
    errorMessage.value = "";

    try {
        const data = await urlData<any>({ url: dataUrl.value });
        // Ensure data has the expected shape for PublishedItem
        page.value = {
            ...data,
            name: data.title || data.name || "Untitled Page",
            title: data.title,
            model_class: "Page",
            username: data.username || data.owner,
        } as PageData;
    } catch (error) {
        errorMessage.value = `Failed to load page: ${error}`;
    } finally {
        loading.value = false;
    }
}

onMounted(() => {
    load();
});

function onEdit() {
    window.location.href = `/pages/editor?id=${props.pageId}`;
}

function stsUrl(config: any) {
    return `${dataUrl.value}/prepare_download`;
}
</script>

<template>
    <div v-if="props.embed" id="columns" class="page-view embed">
        <div id="center" class="container-root">
            <div v-if="loading">
                <LoadingSpan message="Loading Page" />
            </div>
            <div v-else-if="hasError">
                <Heading h1 separator size="lg">Failed to load Page</Heading>
                <BAlert show variant="danger">
                    {{ errorMessage }}
                </BAlert>
            </div>
            <div v-else-if="page && isConfigLoaded" class="page-container">
                <Heading v-if="props.showHeading" h1 separator size="lg" class="page-title">
                    {{ page.title || page.name }}
                </Heading>

                <div class="page-content">
                    <Markdown
                        v-if="page.content_format === 'markdown'"
                        :markdown-config="page"
                        :download-endpoint="stsUrl(config)"
                        :read-only="true"
                        class="page-markdown" />
                    <PageHtml v-else :page="page" />
                </div>
            </div>
            <LoadingSpan v-else-if="page && !isConfigLoaded" message="Loading Galaxy configuration" />
        </div>
    </div>
    <PublishedItem v-else :item="page">
        <template v-slot>
            <div v-if="isConfigLoaded && page">
                <Markdown
                    v-if="page.content_format === 'markdown'"
                    :markdown-config="page"
                    :enable_beta_markdown_export="config.enable_beta_markdown_export"
                    :download-endpoint="stsUrl(config)"
                    :export-link="exportUrl"
                    :read-only="!userOwnsPage"
                    @onEdit="onEdit" />
                <PageHtml v-else :page="page" />
            </div>
            <LoadingSpan v-else message="Loading Galaxy configuration" />
        </template>
    </PublishedItem>
</template>

<style scoped lang="scss">
// Embedded mode styles
.page-view.embed {
    display: flex;
    height: 100%;

    .container-root {
        width: 100%;
        overflow: auto;
    }

    .page-container {
        max-width: 1200px;
        margin: 0 auto;
    }

    .page-title {
        padding: 0 1rem;
        margin-bottom: 2rem;
    }

    .page-content :deep(.page-markdown) {
        max-width: none;
    }
}
</style>
