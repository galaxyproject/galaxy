<script setup lang="ts">
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";
import CollectionDescription from "./Collection/CollectionDescription.vue";
import ContentOptions from "./ContentOptions.vue";
import DatasetDetails from "./Dataset/DatasetDetails.vue";

import { states, hierarchicalCollectionJobStates, type StateKey, type State } from "./model/states";
import { updateContentFields } from "@/components/History/model/queries";
import { JobStateSummary } from "./Collection/JobStateSummary";
import { library } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faArrowCircleUp, faArrowCircleDown, faCheckCircle } from "@fortawesome/free-solid-svg-icons";
import { useEntryPointStore } from "@/stores/entryPointStore";
import { computed } from "vue";
import { useRouter } from "vue-router/composables";

import type { PropType, ComputedRef } from "vue";
import type { HistoryItem } from "@/stores/history/historyItemsStore";

const props = defineProps({
    writable: { type: Boolean, default: true },
    expandDataset: { type: Boolean, required: true },
    highlight: { type: String as PropType<string | null>, default: null },
    id: { type: Number, required: true },
    isDataset: { type: Boolean, default: true },
    isHistoryItem: { type: Boolean, default: false },
    item: { type: Object as PropType<HistoryItem>, required: true },
    name: { type: String, required: true },
    selected: { type: Boolean, default: false },
    selectable: { type: Boolean, default: false },
    filterable: { type: Boolean, default: false },
});

const emit = defineEmits<{
    (e: "update:expand-dataset", isExpanded: boolean): void;
    (e: "update:selected", isSelected: boolean): void;
    (e: "view-collection", item: HistoryItem, name: string): void;
    (e: "tag-change", item: HistoryItem, newTag: string[]): void;
    (e: "tag-click", tag: string): void;
    (e: "toggle-highlights", item: HistoryItem): void;
    (e: "delete"): void;
    (e: "undelete"): void;
    (e: "unhide"): void;
}>();

//@ts-ignore bad library types
library.add(faArrowCircleUp, faArrowCircleDown, faCheckCircle);

const jobState = computed(() => new JobStateSummary(props.item));
const contentId = computed(() => `dataset-${props.item.id}`);

const state: ComputedRef<StateKey> = computed(() => {
    if (props.item.job_state_summary) {
        hierarchicalCollectionJobStates.forEach((state) => {
            if (props.item.job_state_summary[state] ?? 0 > 0) {
                return state;
            }
        });
    }

    return props.item.state ?? "ok";
});

const contentState: ComputedRef<State> = computed(() => states[state.value]);
const contentClass = computed(() => {
    const status = contentState.value?.status;
    if (props.selected) {
        return "alert-info";
    } else if (!status) {
        return `alert-success`;
    } else {
        return `alert-${status}`;
    }
});
const hasTags = computed(() => props.item.tags?.length ?? 0 > 0);
const tagsDisabled = computed(() => !props.writable || !props.expandDataset || !props.isHistoryItem);
const hasStateIcon = computed(() => Object.keys(contentState.value ?? {}).includes("icon"));

/** Relative URLs for history item actions */
const itemUrls = computed(() => {
    const id = props.item.id;
    const isCollection = Object.keys(props.item).includes("collection_type");

    if (isCollection) {
        return {
            edit: `/collection/${id}/edit`,
            showDetails:
                props.item.job_source_id && props.item.job_source_type === "Job"
                    ? `/jobs/${props.item.job_source_id}/view`
                    : null,
        };
    } else {
        return {
            display: `/datasets/${id}/preview`,
            edit: `/datasets/${id}/edit`,
            showDetails: `/datasets/${id}/details`,
            reportError: `/datasets/${id}/error`,
            rerun: `/tool_runner/rerun?id=${id}`,
            visualize: `/visualizations?dataset_id=${id}`,
        };
    }
});

function onClick() {
    if (props.isDataset) {
        emit("update:expand-dataset", !props.expandDataset);
    } else {
        emit("view-collection", props.item, props.name);
    }
}

function onKeyDown(event: KeyboardEvent) {
    if (!(event.target as Element).classList.contains("content-item")) {
        return;
    } else if (event.key === "Enter" || event.key === " ") {
        onClick();
    }
}

const { getEntryPointsForHda } = useEntryPointStore();
const router = useRouter();

function onDisplay() {
    const entryPointsForHda = getEntryPointsForHda(props.item.id);
    const firstEntryPoint = entryPointsForHda?.[0];

    if (firstEntryPoint) {
        const url = firstEntryPoint.target;
        window.open(url, "_blank");
    } else {
        if (itemUrls.value.display) {
            router.push({ path: itemUrls.value.display, params: { title: props.name } });
        } else {
            console.error(`Error on Display. Item name: ${props.name}. Items Display URL is empty`);
        }
    }
}

function onDragStart(event: DragEvent) {
    if (!event.dataTransfer) {
        return;
    }

    event.dataTransfer.dropEffect = "move";
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text", JSON.stringify([props.item]));
}

function onEdit() {
    router.push(itemUrls.value.edit);
}

function onShowCollectionInfo() {
    if (itemUrls.value.showDetails) {
        router.push(itemUrls.value.showDetails);
    } else {
        console.error(`Error on Show Collection Info. Item name: ${props.name}. Items Details URL is empty`);
    }
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

function toggleHighlights() {
    emit("toggle-highlights", props.item);
}
</script>

<template>
    <div class="content-item-spacer">
        <div
            :id="contentId"
            :class="['content-item p-0 rounded btn-transparent-background', contentClass]"
            :data-hid="id"
            :data-state="state"
            tabindex="0"
            role="button"
            @keydown="onKeyDown">
            <div class="p-1 cursor-pointer" draggable @dragstart="onDragStart" @click.stop="onClick">
                <div class="d-flex justify-content-between">
                    <span class="p-1 font-weight-bold">
                        <b-button
                            v-if="selectable"
                            class="selector p-0"
                            @click.stop="emit('update:selected', !selected)">
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
                        @delete="() => emit('delete')"
                        @display="onDisplay"
                        @showCollectionInfo="onShowCollectionInfo"
                        @edit="onEdit"
                        @undelete="() => emit('undelete')"
                        @unhide="() => emit('unhide')" />
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
                :value="props.item.tags"
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

    // improve focus visibility
    &:deep(.btn:focus) {
        box-shadow: 0 0 0 0.2rem transparentize($brand-primary, 0.75);
    }
}

.content-item-spacer {
    padding: 0.125rem 0.25rem;
}
</style>
