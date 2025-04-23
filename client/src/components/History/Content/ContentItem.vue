<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCheckSquare, faSquare } from "@fortawesome/free-regular-svg-icons";
import {
    faArrowCircleDown,
    faArrowCircleUp,
    faCheckCircle,
    faExchangeAlt,
    faSpinner,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBadge, BButton, BCollapse } from "bootstrap-vue";
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router/composables";

import type { ItemUrls } from "@/components/History/Content/Dataset/index";
import { updateContentFields } from "@/components/History/model/queries";
import { useEntryPointStore } from "@/stores/entryPointStore";
import { useEventStore } from "@/stores/eventStore";
import { clearDrag } from "@/utils/setDrag";

import { JobStateSummary } from "./Collection/JobStateSummary";
import { getContentItemState, type StateMap, STATES } from "./model/states";

import CollectionDescription from "./Collection/CollectionDescription.vue";
import ContentOptions from "./ContentOptions.vue";
import DatasetDetails from "./Dataset/DatasetDetails.vue";
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";

library.add(faArrowCircleUp, faArrowCircleDown, faCheckCircle, faExchangeAlt, faSpinner);

const router = useRouter();
const route = useRoute();

interface Props {
    id: number;
    item: any;
    name: string;
    expandDataset?: boolean;
    writable?: boolean;
    addHighlightBtn?: boolean;
    highlight?: string;
    isDataset?: boolean;
    isRangeSelectAnchor?: boolean;
    isHistoryItem?: boolean;
    selected?: boolean;
    selectable?: boolean;
    filterable?: boolean;
    isPlaceholder?: boolean;
    isSubItem?: boolean;
    hasPurgeOption?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    expandDataset: false,
    writable: true,
    addHighlightBtn: false,
    highlight: undefined,
    isDataset: true,
    isRangeSelectAnchor: false,
    isHistoryItem: false,
    selected: false,
    selectable: false,
    filterable: false,
    isPlaceholder: false,
    isSubItem: false,
    hasPurgeOption: false,
});

const emit = defineEmits<{
    (e: "update:selected", selected: boolean): void;
    (e: "update:expand-dataset", expand: boolean): void;
    (e: "shift-arrow-select", direction: string): void;
    (e: "init-key-selection"): void;
    (e: "arrow-navigate", direction: string): void;
    (e: "hide-selection"): void;
    (e: "select-all"): void;
    (e: "selected-to"): void;
    (e: "delete", item: any, recursive: boolean): void;
    (e: "purge"): void;
    (e: "undelete"): void;
    (e: "unhide"): void;
    (e: "view-collection", item: any, name: string): void;
    (e: "drag-start", evt: DragEvent): void;
    (e: "tag-change", item: any, newTags: Array<string>): void;
    (e: "tag-click", tag: string): void;
    (e: "toggleHighlights", item: any): void;
}>();

const entryPointStore = useEntryPointStore();
const eventStore = useEventStore();

const contentItem = ref<HTMLElement | null>(null);
const subItemsVisible = ref(false);

const jobState = computed(() => {
    return new JobStateSummary(props.item);
});

const contentId = computed(() => {
    return `dataset-${props.item.id}`;
});

const contentCls = computed(() => {
    const status = contentState.value && contentState.value.status;
    if (props.item.accessible === false) {
        return "alert-inaccessible";
    } else if (props.selected) {
        return "alert-info";
    } else if (!status) {
        return `alert-success`;
    } else {
        return `alert-${status}`;
    }
});
const computedClass = computed(() => {
    return {
        "content-item m-1 p-0 rounded btn-transparent-background": true,
        [contentCls.value]: true,
        "being-used": Object.values(itemUrls.value).includes(route.path),
        "range-select-anchor": props.isRangeSelectAnchor,
        "sub-item": props.isSubItem,
    };
});
const contentState = computed(() => {
    return STATES[state.value] && STATES[state.value];
});

const hasTags = computed(() => {
    return tags.value && tags.value.length > 0;
});

const hasStateIcon = computed(() => {
    return contentState.value && contentState.value.icon;
});

const state = computed<keyof StateMap>(() => {
    if (props.isPlaceholder) {
        return "placeholder";
    }
    return getContentItemState(props.item);
});

const dataState = computed(() => {
    if (props.item.accessible === false) {
        return "inaccessible";
    } else if (state.value === "new_populated_state") {
        return "new";
    } else {
        return state.value;
    }
});

const tags = computed(() => {
    return props.item.tags;
});

const tagsDisabled = computed(() => {
    return !props.writable || !props.expandDataset || !props.isHistoryItem;
});

const isCollection = computed(() => {
    return "collection_type" in props.item;
});

const itemUrls = computed<ItemUrls>(() => {
    const id = props.item.id;
    if (isCollection.value) {
        return {
            edit: `/collection/${id}/edit`,
            showDetails:
                props.item.job_source_id && props.item.job_source_type === "Job"
                    ? `/jobs/${props.item.job_source_id}/view`
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
});

/** Based on the user's keyboard platform, checks if it is the
 * typical key for selection (ctrl for windows/linux, cmd for mac)
 */
function isSelectKey(event: KeyboardEvent) {
    return eventStore.isMac ? event.metaKey : event.ctrlKey;
}

function onKeyDown(event: KeyboardEvent) {
    const classList = (event.target as HTMLElement)?.classList;
    if (!classList.contains("content-item") || classList.contains("sub-item")) {
        return;
    }

    if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        onClick();
    } else if ((event.key === "ArrowUp" || event.key === "ArrowDown") && !event.shiftKey) {
        event.preventDefault();
        emit("arrow-navigate", event.key);
    }

    if (props.writable) {
        if (event.key === "Tab") {
            emit("init-key-selection");
        } else {
            event.preventDefault();
            if ((event.key === "ArrowUp" || event.key === "ArrowDown") && event.shiftKey) {
                emit("shift-arrow-select", event.key);
            } else if (event.key === "ArrowUp" || event.key === "ArrowDown") {
                emit("init-key-selection");
            } else if (event.key === "Delete" && !props.selected && !props.item.deleted) {
                onDelete(event.shiftKey);
                emit("arrow-navigate", "ArrowDown");
            } else if (event.key === "Escape") {
                emit("hide-selection");
            } else if (event.key === "a" && isSelectKey(event)) {
                emit("select-all");
            }
        }
    }
}

function onClick(e?: Event) {
    const event = e as KeyboardEvent;
    if (event && props.writable) {
        if (isSelectKey(event)) {
            emit("init-key-selection");
            emit("update:selected", !props.selected);
            return;
        } else if (event.shiftKey) {
            emit("selected-to");
            return;
        } else {
            emit("init-key-selection");
        }
    }
    if (props.isPlaceholder) {
        return;
    }
    if (props.isDataset) {
        emit("update:expand-dataset", !props.expandDataset);
    } else {
        emit("view-collection", props.item, props.name);
    }
}

function onDisplay() {
    const entryPointsForHda = entryPointStore.entryPointsForHda(props.item.id);
    if (entryPointsForHda && entryPointsForHda.length > 0) {
        // there can be more than one entry point, choose the first
        const url = entryPointsForHda[0]?.target;
        window.open(url, "_blank");
    } else {
        // vue-router 4 supports a native force push with clean URLs,
        // but we're using a __vkey__ bit as a workaround
        // Only conditionally force to keep urls clean most of the time.
        if (route.path === itemUrls.value.display) {
            // @ts-ignore - monkeypatched router, drop with migration.
            router.push(itemUrls.value.display, { title: props.name, force: true });
        } else if (itemUrls.value.display) {
            // @ts-ignore - monkeypatched router, drop with migration.
            router.push(itemUrls.value.display, { title: props.name });
        }
    }
}

function onDelete(recursive = false) {
    emit("delete", props.item, recursive);
    emit("update:selected", false);
    emit("init-key-selection");
}

function onUndelete() {
    emit("undelete");
    emit("update:selected", false);
    emit("init-key-selection");
}

function onDragStart(evt: DragEvent) {
    emit("drag-start", evt);
}

function onDragEnd() {
    clearDrag();
}

function onEdit() {
    router.push(itemUrls.value.edit!);
}

function onShowCollectionInfo() {
    router.push(itemUrls.value.showDetails!);
}

function onTags(newTags: string[]) {
    emit("tag-change", props.item, newTags);
    updateContentFields(props.item, { tags: newTags });
}

function onTagClick(tag: string) {
    if (props.filterable) {
        emit("tag-click", tag);
    }
}

function onButtonSelect(e: Event) {
    const event = e as KeyboardEvent;
    if (event.shiftKey) {
        onClick(e);
    } else {
        emit("init-key-selection");
    }
    contentItem.value?.focus();
    emit("update:selected", !props.selected);
}

function toggleHighlights() {
    emit("toggleHighlights", props.item);
}

function unexpandedClick(event: Event) {
    if (!props.expandDataset) {
        onClick(event);
    }
}
</script>

<template>
    <div
        :id="contentId"
        ref="contentItem"
        :class="computedClass"
        :data-hid="id"
        :data-state="dataState"
        tabindex="0"
        role="button"
        :draggable="props.item.accessible === false || props.isSubItem || subItemsVisible ? false : true"
        @dragstart="onDragStart"
        @dragend="onDragEnd"
        @keydown="onKeyDown">
        <!-- eslint-disable-next-line vuejs-accessibility/click-events-have-key-events, vuejs-accessibility/no-static-element-interactions -->
        <div class="p-1 cursor-pointer" @click.stop="onClick">
            <div class="d-flex justify-content-between">
                <span class="p-1" data-description="content item header info">
                    <BButton v-if="selectable" class="selector p-0" @click.stop="onButtonSelect">
                        <FontAwesomeIcon v-if="selected" fixed-width size="lg" :icon="faCheckSquare" />
                        <FontAwesomeIcon v-else fixed-width size="lg" :icon="faSquare" />
                    </BButton>
                    <BButton
                        v-if="highlight == 'input'"
                        v-b-tooltip.hover
                        variant="link"
                        class="p-0"
                        title="Input"
                        @click.stop="toggleHighlights">
                        <FontAwesomeIcon class="text-info" :icon="faArrowCircleUp" />
                    </BButton>
                    <BButton
                        v-else-if="highlight == 'active'"
                        v-b-tooltip.hover
                        variant="link"
                        class="p-0"
                        title="Inputs/Outputs highlighted for this item"
                        @click.stop="toggleHighlights"
                        @keypress="toggleHighlights">
                        <FontAwesomeIcon :icon="faCheckCircle" />
                    </BButton>
                    <BButton
                        v-else-if="highlight == 'output'"
                        v-b-tooltip.hover
                        variant="link"
                        class="p-0"
                        title="Output"
                        @click.stop="toggleHighlights">
                        <FontAwesomeIcon class="text-info" :icon="faArrowCircleDown" />
                    </BButton>
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
                <span v-if="item.purged" class="ml-auto align-self-start btn-group p-1">
                    <BBadge variant="secondary" title="This dataset has been permanently deleted">
                        <icon icon="burn" /> Purged
                    </BBadge>
                </span>
                <span class="align-self-start btn-group">
                    <BButton
                        v-if="item.sub_items?.length && !isSubItem"
                        v-b-tooltip.hover
                        title="Show converted items"
                        tabindex="0"
                        class="display-btn px-1 align-items-center"
                        size="sm"
                        variant="link"
                        @click.prevent.stop="subItemsVisible = !subItemsVisible">
                        <FontAwesomeIcon :icon="faExchangeAlt" />
                        <span class="indicator">{{ item.sub_items?.length }}</span>
                    </BButton>
                    <ContentOptions
                        v-if="!isPlaceholder && !item.purged"
                        :writable="writable"
                        :is-dataset="isDataset"
                        :is-deleted="item.deleted"
                        :is-history-item="isHistoryItem"
                        :is-visible="item.visible"
                        :state="state"
                        :item-urls="itemUrls"
                        :has-purge-option="hasPurgeOption"
                        @delete="onDelete"
                        @purge="emit('purge')"
                        @display="onDisplay"
                        @showCollectionInfo="onShowCollectionInfo"
                        @edit="onEdit"
                        @undelete="onUndelete"
                        @unhide="emit('unhide')" />
                </span>
            </div>
        </div>
        <!-- eslint-disable-next-line vuejs-accessibility/click-events-have-key-events, vuejs-accessibility/no-static-element-interactions -->
        <span @click.stop="unexpandedClick">
            <CollectionDescription
                v-if="!isDataset"
                class="px-2 pb-2 cursor-pointer"
                :job-state-summary="jobState"
                :collection-type="item.collection_type"
                :element-count="item.element_count"
                :elements-datatypes="item.elements_datatypes" />
            <StatelessTags
                v-if="!tagsDisabled || hasTags"
                class="px-2 pb-2"
                :class="{ 'cursor-pointer': !expandDataset }"
                :value="tags"
                :disabled="tagsDisabled"
                :clickable="filterable"
                :use-toggle-link="false"
                @input="onTags"
                @tag-click="onTagClick" />
        </span>
        <!-- collections are not expandable, so we only need the DatasetDetails component here -->
        <BCollapse :visible="expandDataset" class="px-2 pb-2">
            <div v-if="item.accessible === false">You are not allowed to access this dataset</div>
            <DatasetDetails
                v-else-if="expandDataset && item.id"
                :id="item.id"
                :writable="writable"
                :show-highlight="(isHistoryItem && filterable) || addHighlightBtn"
                :item-urls="itemUrls"
                @edit="onEdit"
                @toggleHighlights="toggleHighlights" />
        </BCollapse>
        <slot name="sub_items" :sub-items-visible="subItemsVisible" />
    </div>
</template>

<style lang="scss" scoped>
@import "~bootstrap/scss/_functions.scss";
@import "theme/blue.scss";

.content-item {
    cursor: default;

    .name {
        word-break: break-all;
    }

    .indicator {
        align-items: center;
        border-radius: 50%;
        color: $brand-primary;
        display: flex;
        justify-content: center;
        height: 1.2rem;
        position: absolute;
        top: -0.3rem;
        width: 1.2rem;
    }

    // improve focus visibility
    &:deep(.btn:focus) {
        box-shadow: 0 0 0 0.2rem transparentize($brand-primary, 0.75);
    }

    &.range-select-anchor {
        box-shadow: 0 0 0 0.2rem transparentize($brand-primary, 0.75);
    }

    &.being-used {
        border-left: 0.25rem solid $brand-primary;
        margin-left: 0rem !important;
    }
}
</style>
