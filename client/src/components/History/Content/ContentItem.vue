<template>
    <div
        :id="contentId"
        :class="['content-item m-1 p-0 rounded', clsStatus]"
        draggable
        :data-hid="id"
        :data-state="state"
        @dragstart="onDragStart">
        <div class="p-1 cursor-pointer" @click.stop="onClick">
            <div class="clearfix overflow-hidden">
                <div class="btn-group float-right">
                    <b-button
                        v-if="expandable && state !== 'noPermission' && state !== 'discarded'"
                        :disabled="isUnavailable"
                        :title="displayButtonTitle"
                        class="px-1"
                        size="sm"
                        variant="link"
                        @click.stop="onDisplay">
                        <span class="fa fa-eye" />
                    </b-button>
                    <b-button
                        v-if="writeable && state != 'discarded'"
                        :disabled="isUnavailable"
                        class="px-1"
                        title="Edit attributes"
                        size="sm"
                        variant="link"
                        @click.stop="onEdit">
                        <span class="fa fa-pencil" />
                    </b-button>
                    <b-button
                        v-if="writeable && item.deleted"
                        class="px-1"
                        title="Undelete"
                        size="sm"
                        variant="link"
                        :disabled="isUnavailable"
                        @click.stop="$emit('undelete', item)">
                        <span class="fa fa-trash-restore" />
                    </b-button>
                    <b-button
                        v-else-if="writeable"
                        class="px-1"
                        title="Delete"
                        size="sm"
                        variant="link"
                        :disabled="isUnavailable"
                        @click.stop="$emit('delete', item)">
                        <span class="fa fa-trash" />
                    </b-button>
                    <b-button
                        v-if="writeable && !item.visible"
                        class="px-1"
                        title="Unhide"
                        size="sm"
                        variant="link"
                        @click.stop="$emit('unhide', item)">
                        <span class="fa fa-unlock" />
                    </b-button>
                </div>
                <h5 class="float-left p-1 w-75 font-weight-bold">
                    <div v-if="selectable" class="selector float-left mr-2">
                        <span
                            v-if="selected"
                            class="fa fa-lg fa-check-square-o"
                            @click.stop="$emit('update:selected', false)" />
                        <span v-else class="fa fa-lg fa-square-o" @click.stop="$emit('update:selected', true)" />
                    </div>
                    <span :class="icon" />
                    <span class="id hid">{{ id }}</span>
                    <span>:</span>
                    <span class="content-title name">{{ name }}</span>
                    <ContentDescription :item="item" />
                    <div v-if="!expanded && item.tags && item.tags.length > 0" class="nametags">
                        <Nametag v-for="tag in item.tags" :key="tag" :tag="tag" />
                    </div>
                </h5>
            </div>
        </div>
        <DatasetDetails v-if="expanded" @edit="onEdit" :item="item" />
    </div>
</template>

<script>
import { backboneRoute, useGalaxy, iframeRedirect } from "components/plugins/legacyNavigation";
import { Nametag } from "components/Nametags";
import ContentDescription from "./ContentDescription";
import DatasetDetails from "./Dataset/DatasetDetails";
import CONTENTSTATE from "./contentState";

export default {
    components: {
        ContentDescription,
        DatasetDetails,
        Nametag,
    },
    props: {
        item: { type: Object, required: true },
        id: { type: Number, required: true },
        name: { type: String, required: true },
        state: { type: String, default: null },
        expanded: { type: Boolean, required: true },
        selected: { type: Boolean, default: false },
        expandable: { type: Boolean, default: true },
        selectable: { type: Boolean, default: false },
        writeable: { type: Boolean, default: true },
    },
    computed: {
        contentId() {
            return `dataset-${this.item.id}`;
        },
        clsStatus() {
            const status = CONTENTSTATE[this.state] && CONTENTSTATE[this.state].status;
            if (this.selected) {
                return "alert-info";
            } else if (!status) {
                return `alert-success`;
            } else {
                return `alert-${status}`;
            }
        },
        displayButtonTitle() {
            if (this.item.purged) {
                return "Cannot display datasets removed from disk.";
            }
            if (this.isUnavailable) {
                return "This dataset is not yet viewable.";
            }
            return "Display";
        },
        deleteButtonTitle() {
            return this.item.purged
                ? "This dataset has been permanently deleted."
                : this.item.deleted
                ? "Undelete"
                : "Delete";
        },
        editButtonTitle() {
            if (this.item.deleted) {
                return "Undelete this dataset to edit attributes.";
            }
            if (this.item.purged) {
                return "Cannot edit attributes of datasets removed from disk.";
            }
            if (this.isUnavailable) {
                return "This dataset is not yet editable.";
            }
            return "Edit Attributes";
        },
        icon() {
            const stateIcon = CONTENTSTATE[this.state] && CONTENTSTATE[this.state].icon;
            if (stateIcon) {
                return `fa fa-${stateIcon}`;
            }
            return null;
        },
        isUnavailable() {
            return this.item.purged || ["upload", "new"].includes(this.state);
        },
    },
    methods: {
        onDragStart(evt) {
            evt.dataTransfer.dropEffect = "move";
            evt.dataTransfer.effectAllowed = "move";
            evt.dataTransfer.setData("text", JSON.stringify([this.item]));
        },
        onDisplay() {
            const id = this.item.id;
            useGalaxy((Galaxy) => {
                if (Galaxy.frame && Galaxy.frame.active) {
                    Galaxy.frame.addDataset(id);
                } else {
                    iframeRedirect(`datasets/${id}/display/?preview=True`);
                }
            });
        },
        onEdit() {
            if (this.item.collection_type) {
                backboneRoute(`collection/edit/${this.item.id}`);
            } else {
                backboneRoute("datasets/edit", { dataset_id: this.item.id });
            }
        },
        onClick() {
            if (this.expandable) {
                this.$emit("update:expanded", !this.expanded);
            } else {
                this.$emit("drilldown", this.item);
            }
        },
    },
};
</script>
<style>
.content-item:hover {
    filter: brightness(105%);
}
.content-item {
    .name {
        word-wrap: break-word;
    }
}
</style>
