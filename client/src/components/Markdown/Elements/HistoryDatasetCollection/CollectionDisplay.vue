<template>
    <div class="w-50 p-2 float-left">
        <b-card body-class="p-0">
            <b-card-header>
                <span>
                    <span>Dataset Collection:</span>
                    <span class="font-weight-light">{{ collectionName }}</span>
                </span>
            </b-card-header>
            <b-card-body>
                <LoadingSpan v-if="loading" message="Loading Collection" />
                <div v-else class="content-height">
                    <CollectionTree :node="itemContent" :skip-head="true" />
                </div>
            </b-card-body>
        </b-card>
    </div>
</template>

<script>
import axios from "axios";
import CollectionTree from "./CollectionTree";
import LoadingSpan from "components/LoadingSpan";
export default {
    components: {
        CollectionTree,
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
        };
    },
    created() {
        this.getContent().then((data) => {
            this.itemContent = data;
            this.loading = false;
        });
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
    },
    methods: {
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
}
</style>
