<template>
    <PublishedItem :item="page">
        <template v-slot>
            <div v-if="isConfigLoaded">
                <Markdown
                    v-if="page.content_format == 'markdown'"
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

<script>
import { storeToRefs } from "pinia";

import { useConfig } from "@/composables/config";
import { useUserStore } from "@/stores/userStore";
import { withPrefix } from "@/utils/redirect";
import { urlData } from "@/utils/url";

import PageHtml from "./PageHtml.vue";
import PublishedItem from "@/components/Common/PublishedItem.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import Markdown from "@/components/Markdown/Markdown.vue";

export default {
    components: {
        LoadingSpan,
        Markdown,
        PageHtml,
        PublishedItem,
    },
    props: {
        pageId: {
            type: String,
            required: true,
        },
    },
    setup() {
        const { config, isConfigLoaded } = useConfig(true);
        const userStore = useUserStore();
        const { currentUser } = storeToRefs(userStore);
        return { config, currentUser, isConfigLoaded };
    },
    data() {
        return {
            page: {},
        };
    },
    computed: {
        userOwnsPage() {
            return this.currentUser?.username === this.page.username;
        },
        dataUrl() {
            return `/api/pages/${this.pageId}`;
        },
        exportUrl() {
            return `${this.dataUrl}.pdf`;
        },
        editUrl() {
            return `/pages/editor?id=${this.pageId}`;
        },
    },
    created() {
        urlData({ url: this.dataUrl }).then((data) => {
            this.page = data;
        });
    },
    methods: {
        onEdit() {
            window.location = withPrefix(this.editUrl);
        },
        stsUrl(config) {
            return `${this.dataUrl}/prepare_download`;
        },
    },
};
</script>
