<script setup lang="ts">
import { prependPath } from "@/utils/redirect";
import { computed } from "vue";
import type { PropType } from "vue";
import type { StateKey } from "./model/states";
import type { ItemUrls } from "./types";

const props = defineProps({
    writable: { type: Boolean, default: true },
    isDataset: { type: Boolean, required: true },
    isDeleted: { type: Boolean, default: false },
    isHistoryItem: { type: Boolean, required: true },
    isVisible: { type: Boolean, default: true },
    state: { type: String as PropType<StateKey | "">, default: "" },
    itemUrls: { type: Object as PropType<ItemUrls>, required: true },
    keyboardSelectable: { type: Boolean, default: true },
});

const displayDisabled = computed(() => ["discarded", "new", "upload", "queued"].includes(props.state));
const displayButtonTitle = computed(() => {
    if (displayDisabled.value) {
        return "This dataset is not yet viewable";
    } else {
        return "Display";
    }
});

const editDisabled = computed(() =>
    ["discarded", "new", "upload", "queued", "running", "waiting"].includes(props.state)
);
const editButtonTitle = computed(() => {
    if (editDisabled.value) {
        return "This dataset is not yet editable";
    } else {
        return "Edit attributes";
    }
});

const displayUrl = computed(() => prependPath(props.itemUrls.display ?? ""));
const editUrl = computed(() => prependPath(props.itemUrls.edit));
const showCollectionDetailsUrl = computed(() => prependPath(props.itemUrls.showDetails ?? ""));

const tabindex = computed(() => (props.keyboardSelectable ? "0" : "1"));
</script>

<template>
    <span class="align-self-start btn-group">
        <!-- Special case for collections -->
        <b-button
            v-if="!props.isDataset && Boolean(props.itemUrls.showDetails)"
            class="collection-job-details-btn px-1"
            title="Show Details"
            size="sm"
            variant="link"
            :href="showCollectionDetailsUrl"
            @click.prevent.stop="$emit('showCollectionInfo')">
            <icon icon="info-circle" />
        </b-button>

        <!-- Common for all content items -->
        <b-button
            v-if="isDataset"
            :disabled="displayDisabled"
            :title="displayButtonTitle"
            :tabindex="tabindex"
            class="display-btn px-1"
            size="sm"
            variant="link"
            :href="displayUrl"
            @click.prevent.stop="$emit('display')">
            <icon icon="eye" />
        </b-button>
        <b-button
            v-if="writable && isHistoryItem"
            :disabled="editDisabled"
            :title="editButtonTitle"
            :tabindex="tabindex"
            class="edit-btn px-1"
            size="sm"
            variant="link"
            :href="editUrl"
            @click.prevent.stop="$emit('edit')">
            <icon icon="pen" />
        </b-button>
        <b-button
            v-if="writable && isHistoryItem && !isDeleted"
            :tabindex="tabindex"
            class="delete-btn px-1"
            title="Delete"
            size="sm"
            variant="link"
            @click.stop="$emit('delete')">
            <icon icon="trash" />
        </b-button>
        <b-button
            v-if="writable && isHistoryItem && isDeleted"
            :tabindex="tabindex"
            class="undelete-btn px-1"
            title="Undelete"
            size="sm"
            variant="link"
            @click.stop="$emit('undelete')">
            <icon icon="trash-restore" />
        </b-button>
        <b-button
            v-if="writable && isHistoryItem && !isVisible"
            :tabindex="tabindex"
            class="unhide-btn px-1"
            title="Unhide"
            size="sm"
            variant="link"
            @click.stop="$emit('unhide')">
            <icon icon="eye-slash" />
        </b-button>
    </span>
</template>
