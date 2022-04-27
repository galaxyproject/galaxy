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
                <CurrentUser v-slot="{ user }">
                    <UserHistories v-if="user" v-slot="{ currentHistoryId }" :user="user">
                        <b-button
                            v-if="currentHistoryId"
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
                    </UserHistories>
                </CurrentUser>
            </span>
            <span>
                <span>Dataset Collection:</span>
                <span class="font-weight-light">{{ collectionName }}</span>
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
import { getAppRoot } from "onload/loadConfig";
import CollectionTree from "./CollectionTree";
import LoadingSpan from "components/LoadingSpan";
import CurrentUser from "components/providers/CurrentUser";
import UserHistories from "components/providers/UserHistories";
import { copyCollection } from "components/Markdown/services";

export default {
    components: {
        CollectionTree,
        CurrentUser,
        LoadingSpan,
        UserHistories,
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
