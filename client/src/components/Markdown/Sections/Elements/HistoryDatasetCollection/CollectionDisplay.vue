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

<script>
import axios from "axios";
import LoadingSpan from "components/LoadingSpan";
import { copyCollection } from "components/Markdown/services";
import { getAppRoot } from "onload/loadConfig";
import { mapState } from "pinia";

import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";

import CollectionTree from "./CollectionTree";

export default {
    components: {
        CollectionTree,
        LoadingSpan,
    },
    props: {
        collectionId: {
            type: Object,
            default: null,
        },
    },
    data() {
        return {
            itemContent: null,
            loading: true,
            messageText: null,
            messageVariant: null,
        };
    },
    computed: {
        ...mapState(useUserStore, ["currentUser"]),
        ...mapState(useHistoryStore, ["currentHistoryId"]),
        itemName() {
            return this.itemContent?.name;
        },
        itemUrl() {
            return `${getAppRoot()}api/dataset_collections/${this.collectionId}`;
        },
        downloadUrl() {
            return `${getAppRoot()}api/dataset_collections/${this.collectionId}/download`;
        },
    },
    created() {
        this.getContent().then((data) => {
            this.itemContent = data;
            this.loading = false;
        });
    },
    methods: {
        onCopyCollection(currentHistoryId) {
            const hdcaId = this.collectionId;
            copyCollection(hdcaId, currentHistoryId).then(
                (response) => {
                    this.messageVariant = "success";
                    this.messageText = "Successfully copied to current history.";
                },
                (error) => {
                    this.messageVariant = "danger";
                    this.messageText = error;
                }
            );
        },
        async getContent() {
            try {
                const response = await axios.get(this.itemUrl);
                return response.data;
            } catch (e) {
                return `Failed to retrieve content. ${e}`;
            }
        },
    },
};
</script>
<style scoped>
.content-height {
    max-height: 15rem;
    overflow-y: auto;
}
</style>
