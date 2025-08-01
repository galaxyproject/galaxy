<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, onMounted, ref } from "vue";

import { useConfig } from "@/composables/config";
import { useUserStore } from "@/stores/userStore";
import { urlData } from "@/utils/url";

import Heading from "@/components/Common/Heading.vue";
import PublishedItem from "@/components/Common/PublishedItem.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import Markdown from "@/components/Markdown/Markdown.vue";
import PageHtml from "@/components/PageDisplay/PageHtml.vue";

interface PageData {
    id: string;
    title: string;
    name?: string;
    content: string;
    content_format: string;
    username: string;
    slug: string;
    email_hash?: string;
    tags?: string[];
    model_class?: string;
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
const userOwnsPage = computed(() => currentUser.value?.username === page.value?.username);

async function load() {
    loading.value = true;
    errorMessage.value = "";

    try {
        const data = await urlData({ url: dataUrl.value });
        // Ensure data has the expected shape for PublishedItem
        page.value = {
            ...data,
            name: data.title || data.name,
            model_class: "Page",
        };
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
    <div v-if="props.embed" id="columns" class="page-published embed">
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
            <div v-else-if="page" class="published-page">
                <Heading v-if="props.showHeading" h1 separator size="lg" class="page-title">
                    {{ page.title }}
                </Heading>

                <div class="page-content">
                    <Markdown
                        v-if="page.content_format === 'markdown'"
                        :markdown-config="page"
                        :read-only="true"
                        class="page-markdown" />
                    <PageHtml v-else :page="page" />
                </div>
            </div>
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
@import "theme/blue.scss";

.page-published {
    display: flex;
    height: 100%;

    .container-root {
        width: 100%;
        overflow: auto;
    }

    .published-page {
        max-width: 1200px;
        margin: 0 auto;
        padding: 1rem;

        .page-title {
            margin-bottom: 2rem;
        }

        .page-content {
            background-color: white;
            border-radius: 0.5rem;
            padding: 2rem;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);

            :deep(.page-markdown) {
                max-width: none;
            }
        }

        .page-metadata {
            margin-top: 2rem;
            padding: 1rem;
            background-color: #f8f9fa;
            border-radius: 0.5rem;
            font-size: 0.9rem;

            .page-author,
            .page-tags {
                margin-bottom: 0.5rem;
            }
        }
    }
}

// Embedded mode styles
.page-published.embed {
    .published-page {
        padding: 0;

        .page-content {
            box-shadow: none;
            border-radius: 0;
        }
    }
}
</style>
