<template>
    <div class="dataset history-content">
        <nav class="p-1 cursor-pointer alert-success mb-1"  @click.stop="onExpand">
            <div class="overflow-hidden">
                <div class="float-left pl-1" v-if="selectable">
                    <b-check class="selector" :checked="selected" @change="$emit('update:selected', $event)" />
                </div>
                <div>
                    <b-button
                        v-if="!visible"
                        class="float-right px-1"
                        title="Unhide"
                        size="sm"
                        variant="link"
                        icon="eye-slash"
                        @click.stop="$emit('unhide')" />

                    <b-button
                        v-if="deleted"
                        class="float-right px-1"
                        title="Undelete"
                        size="sm"
                        variant="link"
                        icon="trash-restore"
                        @click.stop="$emit('undelete')" />

                    <b-button
                        class="float-right px-1"
                        title="Delete"
                        size="sm"
                        variant="link"
                        @click.stop="$emit('delete')">
                        <span class="fa fa-trash" />
                    </b-button>

                    <b-button
                        class="float-right px-1"
                        title="Edit"
                        size="sm"
                        variant="link"
                        @click.stop="$emit('edit')">
                        <span class="fa fa-pencil" />
                    </b-button>

                    <b-button
                        class="float-right px-1"
                        title="Display"
                        size="sm"
                        variant="link"
                        @click.stop="$emit('display')">
                        <span class="fa fa-eye" />
                    </b-button>

                    <div class="float-left content-title title p-1 overflow-hidden">
                        <h5 class="text-truncate">
                            <span class="hid" data-description="dataset hid">{{ id }}:</span>
                            <span class="name" data-description="dataset name">{{ name }}</span>
                        </h5>
                    </div>
                </div>
            </div>
            <div v-if="expanded" class="p-3 details">
                <h4 data-description="dataset name">{{ name || "(Dataset Name)" }}</h4>
            </div>
        </nav>
    </div>
</template>

<script>
import Placeholder from "./Placeholder";
import Dataset from "./Dataset/Dataset";
import DatasetCollection from "./DatasetCollection";
//import Subdataset from "./Subdataset";
//import Subcollection from "./Subcollection";

export default {
    components: {
        Placeholder,
        Dataset,
        DatasetCollection,
        //Subdataset,
        //Subcollection,
    },
    props: {
        item: { type: Object, required: true },
        id: { type: Number, required: true },
        name: { type: String, required: true },
        expanded: { type: Boolean, required: true },
        showSelection: { type: Boolean, required: false, default: false },
        index: { type: Number, required: false, default: null },
        rowKey: { type: [Number, String], required: false, default: "" },
        writable: { type: Boolean, required: false, default: true },
    },
    data: () => ({
        suppressFocus: true,
        selected: false,
    }),
    computed: {
        loading() {
            return !this.item;
        },
        contentItemComponent() {
            if (this.item.id === undefined) {
                return "Placeholder";
            }
            return this.historyContentItem();
        },
        selectable() {
            return this.showSelection;
        },
        visible() {
            return this.item.visible;
        },
        deleted() {
            return this.item.isDeleted && !this.item.purged;
        },
    },
    created() {
        this.$root.$on("bv::dropdown::show", () => (this.suppressFocus = true));
        this.$root.$on("bv::dropdown::hide", () => (this.suppressFocus = false));
    },
    methods: {
        onExpand() {
            console.log(this.expanded);
            this.$emit("update:expanded", !this.expanded);
        },
        setFocus(index) {
            if (this.suppressFocus) {
                return;
            }
            const ul = this.$el.closest(".scroller");
            const el = ul.querySelector(`[tabindex="${index}"]`);
            if (el) {
                el.focus();
            }
        },
        historyContentItem() {
            const { history_content_type } = this.item;
            switch (history_content_type) {
                case "dataset":
                    return "Dataset";
                case "dataset_collection":
                    return "DatasetCollection";
                default:
                    return "Placeholder";
            }
        },
        collectionContentItem() {
            const { element_type } = this.item;
            switch (element_type) {
                case "hda":
                    return "Subdataset";
                case "hdca":
                    return "Subcollection";
                default:
                    return "Placeholder";
            }
        },
    },
};
</script>
