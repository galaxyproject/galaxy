<template>
    <GCard body-class="p-0">
        <GCardHeader>
            <span class="float-right">
                <GButton
                    v-b-tooltip.hover
                    :href="downloadUrl"
                    variant="link"
                    size="sm"
                    role="button"
                    title="Download Collection"
                    type="button"
                    class="py-0 px-1">
                    <span class="fa fa-download" />
                </GButton>
                <GButton
                    v-if="vcurrentUser && currentHistoryId"
                    v-b-tooltip.hover
                    href="#"
                    role="button"
                    variant="link"
                    title="Import Collection"
                    type="button"
                    class="py-0 px-1"
                    @click="onCopyCollection(currentHistoryId)">
                    <span class="fa fa-file-import" />
                </GButton>
            </span>
            <span>
                <span>Dataset Collection:</span>
                <span class="font-weight-light">{{ collectionName }}</span>
            </span>
        </GCardHeader>
        <GCardBody>
            <LoadingSpan v-if="loading" message="Loading Collection" />
            <div v-else class="content-height">
                <GAlert v-if="!!messageText" :variant="messageVariant" show>
                    {{ messageText }}
                </GAlert>
                <CollectionTree :node="itemContent" :skip-head="true" />
            </div>
        </GCardBody>
    </GCard>
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

import GAlert from "@/component-library/GAlert.vue";
import GButton from "@/component-library/GButton.vue";
import GCard from "@/component-library/GCard.vue";
import GCardBody from "@/component-library/GCardBody.vue";
import GCardHeader from "@/component-library/GCardHeader.vue";

export default {
    components: {
        GCard,
        GCardHeader,
        GCardBody,
        CollectionTree,
        GAlert,
        GButton,
        LoadingSpan,
    },
    props: {
        args: {
            type: Object,
            default: null,
        },
        collections: {
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
        collectionName() {
            const collection = this.collections[this.args.history_dataset_collection_id];
            return collection && collection.name;
        },
        itemUrl() {
            const collectionId = this.args.history_dataset_collection_id;
            const collection = this.collections[collectionId];
            return collection.url;
        },
        downloadUrl() {
            return `${getAppRoot()}api/dataset_collections/${this.args.history_dataset_collection_id}/download`;
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
            const hdcaId = this.args.history_dataset_collection_id;
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
