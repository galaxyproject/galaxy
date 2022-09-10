<template>
    <div
        :id="contentId"
        :class="['content-item m-1 p-0 rounded btn-transparent-background', contentCls]"
        :data-hid="id"
        :data-state="state">
        <div class="p-1 cursor-pointer" draggable @dragstart="onDragStart" @click.stop="onClick">
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
                    <span v-if="highlight == 'input'" v-b-tooltip.hover title="Input" @click.stop="toggleHighlights">
                        <font-awesome-icon class="text-info" icon="arrow-circle-up" />
                    </span>
                    <span
                        v-else-if="highlight == 'noInputs'"
                        v-b-tooltip.hover
                        title="No Inputs for this item"
                        @click.stop="toggleHighlights">
                        <font-awesome-icon icon="minus-circle" />
                    </span>
                    <span
                        v-else-if="highlight == 'output'"
                        v-b-tooltip.hover
                        title="Inputs highlighted for this item"
                        @click.stop="toggleHighlights">
                        <font-awesome-icon icon="check-circle" />
                    </span>
                    <span v-if="hasStateIcon" class="state-icon">
                        <icon fixed-width :icon="contentState.icon" :spin="contentState.spin" />
                    </span>
                    <span class="id hid">{{ id }}</span>
                    <span>:</span>
                    <span class="content-title name">{{ name }}</span>
                </span>
                <span v-if="item.purged" class="align-self-start btn-group p-1">
                    <b-badge variant="secondary" title="This dataset has been permanently deleted">
                        <icon icon="burn" /> Purged
                    </b-badge>
                </span>
                <ContentOptions
                    v-else
                    :is-dataset="isDataset"
                    :is-deleted="item.deleted"
                    :is-history-item="isHistoryItem"
                    :is-visible="item.visible"
                    :state="state"
                    :item-urls="itemUrls"
                    @delete="$emit('delete')"
                    @display="onDisplay"
                    @edit="onEdit"
                    @undelete="$emit('undelete')"
                    @unhide="$emit('unhide')" />
            </div>
        </div>
        <CollectionDescription
            v-if="!isDataset"
            class="px-2 pb-2"
            :job-state-summary="jobState"
            :collection-type="item.collection_type"
            :element-count="item.element_count"
            :elements-datatypes="item.elements_datatypes" />
        <StatelessTags
            v-if="!tagsDisabled || hasTags"
            class="alltags p-1"
            :value="tags"
            :use-toggle-link="false"
            :disabled="tagsDisabled"
            @tag-click="onTagClick"
            @input="onTags" />
        <!-- collections are not expandable, so we only need the DatasetDetails component here -->
        <b-collapse :visible="expandDataset">
            <DatasetDetails
                v-if="expandDataset"
                :dataset="item"
                :show-highlight="isHistoryItem"
                :item-urls="itemUrls"
                @edit="onEdit"
                @toggleHighlights="toggleHighlights" />
        </b-collapse>
    </div>
</template>

<script>
import { iframeAdd } from "components/plugins/legacyNavigation";
import { StatelessTags } from "components/Tags";
import { STATES, HIERARCHICAL_COLLECTION_JOB_STATES } from "./model/states";
import CollectionDescription from "./Collection/CollectionDescription";
import ContentOptions from "./ContentOptions";
import DatasetDetails from "./Dataset/DatasetDetails";
import { updateContentFields } from "components/History/model/queries";
import { JobStateSummary } from "./Collection/JobStateSummary";
import { library } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faArrowCircleUp, faMinusCircle, faCheckCircle } from "@fortawesome/free-solid-svg-icons";

library.add(faArrowCircleUp, faMinusCircle, faCheckCircle);

export default {
    components: {
        CollectionDescription,
        ContentOptions,
        DatasetDetails,
        StatelessTags,
        FontAwesomeIcon,
    },
    props: {
        expandDataset: { type: Boolean, required: true },
        highlight: { type: String, default: null },
        id: { type: Number, required: true },
        isDataset: { type: Boolean, default: true },
        isHistoryItem: { type: Boolean, default: false },
        item: { type: Object, required: true },
        name: { type: String, required: true },
        selected: { type: Boolean, default: false },
        selectable: { type: Boolean, default: false },
    },
    computed: {
        jobState() {
            return new JobStateSummary(this.item);
        },
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
                for (const state of HIERARCHICAL_COLLECTION_JOB_STATES) {
                    if (this.item.job_state_summary[state] > 0) {
                        return state;
                    }
                }
            } else if (this.item.state) {
                return this.item.state;
            }
            return "ok";
        },
        tags() {
            return this.item.tags;
        },
        tagsDisabled() {
            return !this.expandDataset || !this.isHistoryItem;
        },
        isCollection() {
            return "collection_type" in this.item;
        },
        /** Relative URLs for history item actions */
        itemUrls() {
            const id = this.item.id;
            if (this.isCollection) {
                return {
                    edit: `/collection/edit/${id}`,
                };
            }
            return {
                display: `/datasets/${id}/display/?preview=True`,
                edit: `/datasets/edit/${id}`,
                showDetails: `/datasets/${id}/details`,
                reportError: `/datasets/${id}/error`,
                rerun: `/tool_runner/rerun?id=${id}`,
                visualize: `/visualizations?dataset_id=${id}`,
            };
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
            iframeAdd({ path: this.itemUrls.display, title: this.name });
        },
        onDragStart(evt) {
            evt.dataTransfer.dropEffect = "move";
            evt.dataTransfer.effectAllowed = "move";
            evt.dataTransfer.setData("text", JSON.stringify([this.item]));
        },
        onEdit() {
            this.$router.push(this.itemUrls.edit);
        },
        onTags(newTags) {
            this.$emit("tag-change", this.item, newTags);
            updateContentFields(this.item, { tags: newTags });
        },
        onTagClick(tag) {
            this.$emit("tag-click", tag.label);
        },
        toggleHighlights() {
            this.$emit("toggleHighlights", this.item);
        },
    },
};
</script>
<style lang="scss">
.content-item:hover {
    filter: brightness(105%);
}
.content-item {
    .name {
        word-break: break-all;
    }
}
</style>
