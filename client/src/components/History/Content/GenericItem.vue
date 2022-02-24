<template>
    <component :is="providerComponent" :id="itemId" auto-refresh v-slot="{ result: item, loading }">
        <loading-span v-if="loading" message="Loading dataset" />
        <ContentItem
            v-else
            :item="item"
            :id="item.hid"
            :name="item.name"
            :state="item.state || item.populated_state"
            :expanded="expanded"
            :expandable="item.history_content_type == 'dataset'"
            @update:expanded="expanded = $event"
            @drilldown="drilldown = !drilldown"
            @delete="onDelete"
            @undelete="onUndelete"
            @unhide="onUnhide" />
    </component>
</template>

<script>
import LoadingSpan from "components/LoadingSpan";
import { DatasetProvider, DatasetCollectionProvider } from "components/providers";
import { deleteContent, updateContentFields } from "components/History/model/queries";
import ContentItem from "./ContentItem";

export default {
    components: {
        ContentItem,
        DatasetProvider,
        DatasetCollectionProvider,
        LoadingSpan,
    },
    props: {
        itemId: {
            type: String,
            required: true,
        },
        itemSrc: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            drilldown: false,
            expanded: false,
        };
    },
    created() {
        console.log(this.itemId);
    },
    computed: {
        providerComponent() {
            return this.itemSrc == "hda" ? "DatasetProvider" : "DatasetCollectionProvider";
        },
    },
    methods: {
        onDelete(item) {
            deleteContent(item);
        },
        onUndelete(item) {
            updateContentFields(item, { deleted: false });
        },
        onHide(item) {
            updateContentFields(item, { visible: false });
        },
        onUnhide(item) {
            updateContentFields(item, { visible: true });
        },
    },
};
</script>
