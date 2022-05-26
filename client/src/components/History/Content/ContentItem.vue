<template>
    <div
        :id="contentId"
        :class="['content-item m-1 p-0 rounded', contentCls]"
        draggable
        :data-hid="id"
        :data-state="state"
        @dragstart="onDragStart">
        <div class="p-1 cursor-pointer" @click.stop="onClick">
            <div class="d-flex justify-content-between">
                <span class="p-1 font-weight-bold">
                    <span v-if="selectable" class="selector">
                        <icon
                            v-if="selected"
                            fixed-width
                            size="lg"
                            :icon="['far', 'check-square']"
                            @click.stop="$emit('update:selected', false)" />
                        <icon
                            v-else
                            fixed-width
                            size="lg"
                            :icon="['far', 'square']"
                            @click.stop="$emit('update:selected', true)" />
                    </span>
                    <span v-if="hasStateIcon">
                        <icon fixed-width :icon="contentState.icon" :spin="contentState.spin" />
                    </span>
                    <span class="id hid">{{ id }}</span>
                    <span>:</span>
                    <span class="content-title name">{{ name }}</span>
                    <CollectionDescription
                        v-if="!isDataset"
                        :collection-type="item.collection_type"
                        :element-count="item.element_count"
                        :elements-datatypes="item.elements_datatypes" />
                </span>
                <ContentOptions
                    :is-dataset="isDataset"
                    :is-deleted="item.deleted"
                    :is-history-item="isHistoryItem"
                    :is-purged="item.purged"
                    :is-visible="item.visible"
                    :state="state"
                    @delete="$emit('delete')"
                    @display="onDisplay"
                    @edit="onEdit"
                    @undelete="$emit('undelete')"
                    @unhide="$emit('unhide')" />
            </div>
        </div>
        <StatelessTags
            v-if="!tagsDisabled || hasTags"
            class="alltags p-1"
            :value="tags"
            :use-toggle-link="false"
            :disabled="tagsDisabled"
            @tag-click="onTagClick"
            @input="onTags" />
        <!-- collections are not expandable, so we only need the DatasetDetails component here -->
        <div class="detail-animation-wrapper" :class="expandDataset ? '' : 'collapsed'">
            <DatasetDetails v-if="expandDataset" :dataset="item" @edit="onEdit" />
        </div>
    </div>
</template>

<script>
import { backboneRoute, iframeAdd } from "components/plugins/legacyNavigation";
import { StatelessTags } from "components/Tags";
import { STATES } from "./model/states";
import CollectionDescription from "./Collection/CollectionDescription";
import ContentOptions from "./ContentOptions";
import DatasetDetails from "./Dataset/DatasetDetails";
import { updateContentFields } from "components/History/model/queries";

export default {
    components: {
        CollectionDescription,
        ContentOptions,
        DatasetDetails,
        StatelessTags,
    },
    props: {
        expandDataset: { type: Boolean, required: true },
        id: { type: Number, required: true },
        isDataset: { type: Boolean, default: true },
        isHistoryItem: { type: Boolean, default: true },
        item: { type: Object, required: true },
        name: { type: String, required: true },
        selected: { type: Boolean, default: false },
        selectable: { type: Boolean, default: false },
    },
    computed: {
        contentId() {
            return `dataset-${this.item.id}`;
        },
        contentCls() {
            const status = this.contentState && this.contentState.status;
            if (this.selected) {
                return "alert-info";
            } else if (!status) {
                return `alert-success`;
            } else {
                return `alert-${status}`;
            }
        },
        contentState() {
            return STATES[this.state] && STATES[this.state];
        },
        hasTags() {
            return this.tags && this.tags.length > 0;
        },
        hasStateIcon() {
            return this.contentState && this.contentState.icon;
        },
        state() {
            if (this.item.job_state_summary) {
                for (const key of ["error", "failed", "paused", "upload", "running"]) {
                    if (this.item.job_state_summary[key] > 0) {
                        return key;
                    }
                }
                return "ok";
            } else {
                return this.item.state;
            }
        },
        tags() {
            return this.item.tags;
        },
        tagsDisabled() {
            return !this.expandDataset || !this.isHistoryItem;
        },
    },
    methods: {
        onClick() {
            if (this.isDataset) {
                this.$emit("update:expand-dataset", !this.expandDataset);
            } else {
                this.$emit("view-collection", this.item, this.name);
            }
        },
        onDisplay() {
            const url = `datasets/${this.item.id}/display/?preview=True`;
            iframeAdd({ path: url, title: this.name });
        },
        onDragStart(evt) {
            evt.dataTransfer.dropEffect = "move";
            evt.dataTransfer.effectAllowed = "move";
            evt.dataTransfer.setData("text", JSON.stringify([this.item]));
        },
        onEdit() {
            if (this.item.collection_type) {
                backboneRoute(`collection/edit/${this.item.id}`);
            } else {
                backboneRoute("datasets/edit", { dataset_id: this.item.id });
            }
        },
        onTags(newTags) {
            this.$emit("tag-change", this.item, newTags);
            updateContentFields(this.item, { tags: newTags });
        },
        onTagClick(tag) {
            this.$emit("tag-click", tag.label);
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
        word-break: break-all;
    }
}
.detail-animation-wrapper {
    overflow: hidden;
    transition: max-height 0.2s ease-out;
    height: auto;
    max-height: 400px;
}
.detail-animation-wrapper.collapsed {
    max-height: 0;
}
</style>
