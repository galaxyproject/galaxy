<template>
    <div
        :id="contentId"
        :class="['content-item m-1 p-0 rounded btn-transparent-background', contentCls, isBeingUsed]"
        :data-hid="id"
        :data-state="dataState"
        tabindex="0"
        role="button"
        @keydown="onKeyDown"
        @focus="$emit('update:item-focused')">
        <div class="p-1 cursor-pointer" draggable @dragstart="onDragStart" @dragend="onDragEnd" @click.stop="onClick">
            <div class="d-flex justify-content-between">
                <span class="p-1" data-description="content item header info">
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
                        <FontAwesomeIcon class="text-info" icon="arrow-circle-up" />
                    </b-button>
                    <b-button
                        v-else-if="highlight == 'active'"
                        v-b-tooltip.hover
                        variant="link"
                        class="p-0"
                        title="Inputs/Outputs highlighted for this item"
                        @click.stop="toggleHighlights"
                        @keypress="toggleHighlights">
                        <FontAwesomeIcon icon="check-circle" />
                    </b-button>
                    <b-button
                        v-else-if="highlight == 'output'"
                        v-b-tooltip.hover
                        variant="link"
                        class="p-0"
                        title="Output"
                        @click.stop="toggleHighlights">
                        <FontAwesomeIcon class="text-info" icon="arrow-circle-down" />
                    </b-button>
                    <span v-if="hasStateIcon" class="state-icon">
                        <icon
                            fixed-width
                            :icon="contentState.icon"
                            :spin="contentState.spin"
                            :title="item.populated_state_message || contentState.text" />
                    </span>
                    <span class="id hid">{{ id }}:</span>
                    <span class="content-title name font-weight-bold">{{ name }}</span>
                </span>
                <span v-if="item.purged" class="align-self-start btn-group p-1">
                    <b-badge variant="secondary" title="This dataset has been permanently deleted">
                        <icon icon="burn" /> Purged
                    </b-badge>
                </span>
                <ContentOptions
                    v-if="!isPlaceholder && !item.purged"
                    :writable="writable"
                    :is-dataset="isDataset"
                    :is-deleted="item.deleted"
                    :is-history-item="isHistoryItem"
                    :is-visible="item.visible"
                    :state="state"
                    :item-urls="itemUrls"
                    @delete="onDelete"
                    @display="onDisplay"
                    @showCollectionInfo="onShowCollectionInfo"
                    @edit="onEdit"
                    @undelete="onUndelete"
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
            class="px-2 pb-2"
            :value="tags"
            :disabled="tagsDisabled"
            :clickable="filterable"
            :use-toggle-link="false"
            @input="onTags"
            @tag-click="onTagClick" />
        <!-- collections are not expandable, so we only need the DatasetDetails component here -->
        <b-collapse :visible="expandDataset" class="px-2 pb-2">
            <DatasetDetails
                v-if="expandDataset && item.id"
                :id="item.id"
                :writable="writable"
                :show-highlight="(isHistoryItem && filterable) || addHighlightBtn"
                :item-urls="itemUrls"
                @edit="onEdit"
                @toggleHighlights="toggleHighlights" />
        </b-collapse>
    </div>
</template>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faArrowCircleDown, faArrowCircleUp, faCheckCircle, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { updateContentFields } from "components/History/model/queries";
import StatelessTags from "components/TagsMultiselect/StatelessTags";
import { useEntryPointStore } from "stores/entryPointStore";

import { clearDrag } from "@/utils/setDrag.ts";

import CollectionDescription from "./Collection/CollectionDescription";
import { JobStateSummary } from "./Collection/JobStateSummary";
import ContentOptions from "./ContentOptions";
import DatasetDetails from "./Dataset/DatasetDetails";
import { HIERARCHICAL_COLLECTION_JOB_STATES, STATES } from "./model/states";

library.add(faArrowCircleUp, faArrowCircleDown, faCheckCircle, faSpinner);
export default {
    components: {
        CollectionDescription,
        ContentOptions,
        DatasetDetails,
        StatelessTags,
        FontAwesomeIcon,
    },
    props: {
        id: { type: Number, required: true },
        item: { type: Object, required: true },
        name: { type: String, required: true },
        expandDataset: { type: Boolean, default: false },
        writable: { type: Boolean, default: true },
        addHighlightBtn: { type: Boolean, default: false },
        highlight: { type: String, default: null },
        isDataset: { type: Boolean, default: true },
        isHistoryItem: { type: Boolean, default: false },
        selected: { type: Boolean, default: false },
        selectable: { type: Boolean, default: false },
        filterable: { type: Boolean, default: false },
        isPlaceholder: { type: Boolean, default: false },
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
            if (this.isPlaceholder) {
                return "placeholder";
            }
            if (this.item.populated_state === "failed") {
                return "failed_populated_state";
            }
            if (this.item.populated_state === "new") {
                return "new_populated_state";
            }
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
        dataState() {
            return this.state === "new_populated_state" ? "new" : this.state;
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
        isBeingUsed() {
            return Object.values(this.itemUrls).includes(this.$route.path) ? "being-used" : "";
        },
    },
    methods: {
        isCtrlKey(event) {
            const isMac = navigator.userAgent.indexOf("Mac") >= 0;
            return isMac ? event.metaKey : event.ctrlKey;
        },
        onKeyDown(event) {
            if (!event.target.classList.contains("content-item")) {
                return;
            }

            if (event.key === "Enter" || event.key === " ") {
                this.onClick();
            } else if ((event.key === "ArrowUp" || event.key === "ArrowDown") && event.shiftKey) {
                event.preventDefault();
                this.$emit("shift-select", event.key);
            } else if (event.key === "ArrowUp" || event.key === "ArrowDown") {
                event.preventDefault();
                this.$emit("init-key-selection");
                this.$emit("arrow-navigate", event.key);
            } else if (event.key === "Tab") {
                this.$emit("init-key-selection");
            } else if (event.key === "Delete" && !this.selected && !this.item.deleted) {
                event.preventDefault();
                this.onDelete(event.shiftKey);
            } else if (event.key === "Escape") {
                event.preventDefault();
                this.$emit("hide-selection");
            } else if (event.key === "a" && this.isCtrlKey(event)) {
                event.preventDefault();
                this.$emit("select-all");
            }
        },
        onClick(event) {
            if (event && event.shiftKey && this.isCtrlKey(event)) {
                this.$emit("selected-to", false);
            } else if (event && this.isCtrlKey(event)) {
                this.$emit("init-key-selection");
                this.$emit("update:selected", !this.selected);
            } else if (event && event.shiftKey) {
                this.$emit("selected-to", true);
            } else if (this.isPlaceholder) {
                this.$emit("init-key-selection");
            } else if (this.isDataset) {
                this.$emit("init-key-selection");
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
                // vue-router 4 supports a native force push with clean URLs,
                // but we're using a workaround with a __vkey__ bit as a workaround
                // Only conditionally force to keep urls clean most of the time.
                if (this.$router.currentRoute.path === this.itemUrls.display) {
                    this.$router.push(this.itemUrls.display, { title: this.name, force: true });
                } else {
                    this.$router.push(this.itemUrls.display, { title: this.name });
                }
            }
        },
        onDelete(recursive = false) {
            this.$emit("delete", this.item, recursive);
            this.$emit("update:selected", false);
            this.$emit("init-key-selection");
        },
        onUndelete() {
            this.$emit("undelete");
            this.$emit("update:selected", false);
            this.$emit("init-key-selection");
        },
        onDragStart(evt) {
            this.$emit("drag-start", evt);
        },
        onDragEnd() {
            clearDrag();
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

    &.being-used {
        border-left: 0.25rem solid $brand-primary;
        margin-left: 0rem !important;
    }
}
</style>
