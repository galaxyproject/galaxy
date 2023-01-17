<template>
    <div
        :id="contentId"
        :class="['content-item m-1 p-0 rounded btn-transparent-background', contentCls]"
        :data-hid="id"
        :data-state="state"
        tabindex="0"
        role="button"
        @keydown="onKeyDown">
        <div class="p-1 cursor-pointer" draggable @dragstart="onDragStart" @click.stop="onClick">
            <div class="d-flex justify-content-between">
                <span class="p-1 font-weight-bold">
                    <b-button v-if="selectable" class="selector p-0" @click.stop="$emit('update:selected', !selected)">
                        <icon v-if="selected" fixed-width size="lg" :icon="['far', 'check-square']" />
                        <icon v-else fixed-width size="lg" :icon="['far', 'square']" />
                    </b-button>
                    <b-button
                        v-if="highlight == 'input'"
                        v-b-tooltip.hover
                        variant="link"
                        class="p-0"
                        title="Input"
                        @click.stop="toggleHighlights">
                        <font-awesome-icon class="text-info" icon="arrow-circle-up" />
                    </b-button>
                    <b-button
                        v-else-if="highlight == 'active'"
                        v-b-tooltip.hover
                        variant="link"
                        class="p-0"
                        title="Inputs/Outputs highlighted for this item"
                        @click.stop="toggleHighlights"
                        @keypress="toggleHighlights">
                        <font-awesome-icon icon="check-circle" />
                    </b-button>
                    <b-button
                        v-else-if="highlight == 'output'"
                        v-b-tooltip.hover
                        variant="link"
                        class="p-0"
                        title="Output"
                        @click.stop="toggleHighlights">
                        <font-awesome-icon class="text-info" icon="arrow-circle-down" />
                    </b-button>
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
                    :writable="writable"
                    :is-dataset="isDataset"
                    :is-deleted="item.deleted"
                    :is-history-item="isHistoryItem"
                    :is-visible="item.visible"
                    :state="state"
                    :item-urls="itemUrls"
                    :keyboard-selectable="expandDataset"
                    @delete="$emit('delete')"
                    @display="onDisplay"
                    @showCollectionInfo="onShowCollectionInfo"
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
            :value="tags"
            :disabled="tagsDisabled"
            :clickable="filterable"
            :use-toggle-link="false"
            @input="onTags"
            @tag-click="onTagClick" />
        <!-- collections are not expandable, so we only need the DatasetDetails component here -->
        <b-collapse :visible="expandDataset">
            <DatasetDetails
                v-if="expandDataset"
                :dataset="item"
                :writable="writable"
                :show-highlight="isHistoryItem && filterable"
                :item-urls="itemUrls"
                @edit="onEdit"
                @toggleHighlights="toggleHighlights" />
        </b-collapse>
    </div>
</template>

<script>
import StatelessTags from "components/TagsMultiselect/StatelessTags";
import { STATES, HIERARCHICAL_COLLECTION_JOB_STATES } from "./model/states";
import CollectionDescription from "./Collection/CollectionDescription";
import ContentOptions from "./ContentOptions";
import DatasetDetails from "./Dataset/DatasetDetails";
import { updateContentFields } from "components/History/model/queries";
import { JobStateSummary } from "./Collection/JobStateSummary";
import { library } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faArrowCircleUp, faArrowCircleDown, faCheckCircle } from "@fortawesome/free-solid-svg-icons";
import { useEntryPointStore } from "stores/entryPointStore";

library.add(faArrowCircleUp, faArrowCircleDown, faCheckCircle);
export default {
    components: {
        CollectionDescription,
        ContentOptions,
        DatasetDetails,
        StatelessTags,
        FontAwesomeIcon,
    },
    props: {
        writable: { type: Boolean, default: true },
        expandDataset: { type: Boolean, required: true },
        highlight: { type: String, default: null },
        id: { type: Number, required: true },
        isDataset: { type: Boolean, default: true },
        isHistoryItem: { type: Boolean, default: false },
        item: { type: Object, required: true },
        name: { type: String, required: true },
        selected: { type: Boolean, default: false },
        selectable: { type: Boolean, default: false },
        filterable: { type: Boolean, default: false },
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
            return !this.writable || !this.expandDataset || !this.isHistoryItem;
        },
        isCollection() {
            return "collection_type" in this.item;
        },
        /** Relative URLs for history item actions */
        itemUrls() {
            const id = this.item.id;
            if (this.isCollection) {
                return {
                    edit: `/collection/${id}/edit`,
                    showDetails:
                        this.item.job_source_id && this.item.job_source_type === "Job"
                            ? `/jobs/${this.item.job_source_id}/view`
                            : null,
                };
            }
            return {
                display: `/datasets/${id}/preview`,
                edit: `/datasets/${id}/edit`,
                showDetails: `/datasets/${id}/details`,
                reportError: `/datasets/${id}/error`,
                rerun: `/tool_runner/rerun?id=${id}`,
                visualize: `/visualizations?dataset_id=${id}`,
            };
        },
    },
    methods: {
        onKeyDown(event) {
            if (!event.target.classList.contains("content-item")) {
                return;
            }

            if (event.key === "Enter" || event.key === " ") {
                this.onClick();
            }
        },
        onClick() {
            if (this.isDataset) {
                this.$emit("update:expand-dataset", !this.expandDataset);
            } else {
                this.$emit("view-collection", this.item, this.name);
            }
        },
        onDisplay() {
            const entryPointStore = useEntryPointStore();
            const entryPointsForHda = entryPointStore.entryPointsForHda(this.item.id);
            if (entryPointsForHda && entryPointsForHda.length > 0) {
                // there can be more than one entry point, choose the first
                const url = entryPointsForHda[0].target;
                window.open(url, "_blank");
            } else {
                this.$router.push(this.itemUrls.display, { title: this.name });
            }
        },
        onDragStart(evt) {
            evt.dataTransfer.dropEffect = "move";
            evt.dataTransfer.effectAllowed = "move";
            evt.dataTransfer.setData("text", JSON.stringify([this.item]));
        },
        onEdit() {
            this.$router.push(this.itemUrls.edit);
        },
        onShowCollectionInfo() {
            this.$router.push(this.itemUrls.showDetails);
        },
        onTags(newTags) {
            this.$emit("tag-change", this.item, newTags);
            updateContentFields(this.item, { tags: newTags });
        },
        onTagClick(tag) {
            if (this.filterable) {
                this.$emit("tag-click", tag);
            }
        },
        toggleHighlights() {
            this.$emit("toggleHighlights", this.item);
        },
    },
};
</script>

<style lang="scss" scoped>
@import "~bootstrap/scss/_functions.scss";
@import "theme/blue.scss";

.content-item {
    cursor: default;

    .name {
        word-break: break-all;
    }

    // improve focus visibility
    &:deep(.btn:focus) {
        box-shadow: 0 0 0 0.2rem transparentize($brand-primary, 0.75);
    }
}
</style>
