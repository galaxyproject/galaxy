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

import { getGalaxyInstance } from "@/app";
import type { ItemUrls } from "@/components/History/Content/Dataset/index";
import { updateContentFields } from "@/components/History/model/queries";
import { useEntryPointStore } from "@/stores/entryPointStore";
import { clearDrag } from "@/utils/setDrag";

import { getContentItemState, type State, STATES } from "./model/states";
import type { RouterPushOptions } from "./router-push-options";

import CollectionDescription from "./Collection/CollectionDescription.vue";
import ContentExpirationIndicator from "./ContentExpirationIndicator.vue";
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
    getItemKey?: (item: any) => string;
    selectClickHandler?: (item: any, event: Event) => boolean;
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
    getItemKey: (item: any) => {
        return `${item.history_content_type}-${item.id}`;
    },
    selectClickHandler: (item: any, event: Event) => {
        return true;
    },
});

const emit = defineEmits<{
    (e: "update:selected", selected: boolean): void;
    (e: "update:expand-dataset", expand: boolean): void;
    (e: "init-key-selection"): void;
    (e: "delete", item: any, recursive: boolean): void;
    (e: "undelete"): void;
    (e: "unhide"): void;
    (e: "view-collection", item: any, name: string): void;
    (e: "drag-start", evt: DragEvent): void;
    (e: "tag-change", item: any, newTags: Array<string>): void;
    (e: "tag-click", tag: string): void;
    (e: "toggleHighlights", item: any): void;
    (e: "on-key-down", event: KeyboardEvent): void;
}>();

const entryPointStore = useEntryPointStore();

const contentItem = ref<HTMLElement | null>(null);
const subItemsVisible = ref(false);

const itemIsRunningInteractiveTool = computed(() => {
    // If our dataset id is in the entrypOintStore it's a running it
    return !isCollection.value && entryPointStore.entryPointsForHda(props.item.id).length > 0;
});

const contentId = computed(() => props.getItemKey(props.item));

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

const state = computed<State>(() => {
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
    return "collection_type" in props.item || props.item.element_type === "dataset_collection";
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
    let display = `/datasets/${id}`;
    if (props.item.extension == "tool_markdown") {
        display = `/datasets/${id}/report`;
    }
    return {
        display: display,
        edit: `/datasets/${id}/edit`,
        showDetails: `/datasets/${id}/details`,
        reportError: `/datasets/${id}/error`,
        rerun: `/tool_runner/rerun?id=${id}`,
        visualize: `/visualizations?dataset_id=${id}`,
    };
});

function onKeyDown(event: KeyboardEvent) {
    const classList = (event.target as HTMLElement)?.classList;
    if (!classList.contains("content-item") || classList.contains("sub-item")) {
        return;
    }

    if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        onClick();
    } else {
        emit("on-key-down", event);
    }
}

function onClick(e?: Event) {
    const event = e as KeyboardEvent;
    if (event && props.writable && !props.selectClickHandler(props.item, event)) {
        return;
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
        const Galaxy = getGalaxyInstance();
        const isWindowManagerActive = Galaxy.frame && Galaxy.frame.active;

        // Build the display URL with displayOnly query param if needed
        let displayUrl = itemUrls.value.display;
        if (isWindowManagerActive && displayUrl) {
            displayUrl += displayUrl.includes("?") ? "&displayOnly=true" : "?displayOnly=true";
        }

        // vue-router 4 supports a native force push with clean URLs,
        // but we're using a __vkey__ bit as a workaround
        // Only conditionally force to keep urls clean most of the time.
        if (route.path === itemUrls.value.display) {
            const options: RouterPushOptions = {
                force: true,
                preventWindowManager: !isWindowManagerActive,
                title: isWindowManagerActive ? `${props.item.hid}: ${props.name}` : undefined,
            };
            // @ts-ignore - monkeypatched router, drop with migration.
            router.push(displayUrl, options);
        } else if (displayUrl) {
            const options: RouterPushOptions = {
                preventWindowManager: !isWindowManagerActive,
                title: isWindowManagerActive ? `${props.item.hid}: ${props.name}` : undefined,
            };
            // @ts-ignore - monkeypatched router, drop with migration.
            router.push(displayUrl, options);
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

function onView() {
    router.push(itemUrls.value.view!);
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
                        :is-running-interactive-tool="itemIsRunningInteractiveTool"
                        :interactive-tool-id="
                            itemIsRunningInteractiveTool ? entryPointStore.entryPointsForHda(item.id)[0]?.id : ''
                        "
                        @delete="onDelete"
                        @display="onDisplay"
                        @view="onView"
                        @showCollectionInfo="onShowCollectionInfo"
                        @edit="onEdit"
                        @undelete="onUndelete"
                        @unhide="emit('unhide')" />
                </span>
            </div>
        </div>
        <ContentExpirationIndicator :item="item" class="ml-auto align-self-start btn-group p-1" />
        <!-- eslint-disable-next-line vuejs-accessibility/click-events-have-key-events, vuejs-accessibility/no-static-element-interactions -->
        <span @click.stop="unexpandedClick">
            <CollectionDescription v-if="!isDataset" class="px-2 pb-2 cursor-pointer" :hdca="item" />
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
