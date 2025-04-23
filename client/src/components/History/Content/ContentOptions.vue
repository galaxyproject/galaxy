<script setup lang="ts">
import { BButton, BDropdown } from "bootstrap-vue";
import { computed, type Ref, ref } from "vue";

import { prependPath } from "@/utils/redirect";

const props = defineProps({
    writable: { type: Boolean, default: true },
    isDataset: { type: Boolean, required: true },
    isDeleted: { type: Boolean, default: false },
    isHistoryItem: { type: Boolean, required: true },
    isVisible: { type: Boolean, default: true },
    state: { type: String, default: "" },
    itemUrls: { type: Object, required: true },
    hasPurgeOption: { type: Boolean, default: false },
});

const emit = defineEmits<{
    (e: "display"): void;
    (e: "showCollectionInfo"): void;
    (e: "edit"): void;
    (e: "delete", recursive?: boolean): void;
    (e: "undelete"): void;
    (e: "unhide"): void;
    (e: "purge"): void;
}>();

const deleteMenu: Ref<BDropdown | null> = ref(null);

const displayButtonTitle = computed(() => (displayDisabled.value ? "This dataset is not yet viewable." : "Display"));

const displayDisabled = computed(() => ["discarded", "new", "upload", "queued"].includes(props.state));

const editButtonTitle = computed(() => (editDisabled.value ? "This dataset is not yet editable." : "Edit attributes"));

const editDisabled = computed(() =>
    ["discarded", "new", "upload", "queued", "running", "waiting"].includes(props.state)
);

const displayUrl = computed(() => prependPath(props.itemUrls.display));

const editUrl = computed(() => prependPath(props.itemUrls.edit));

const isCollection = computed(() => !props.isDataset);

const canShowCollectionDetails = computed(() => props.itemUrls.showDetails);

const showCollectionDetailsUrl = computed(() => prependPath(props.itemUrls.showDetails));

function onDelete($event: MouseEvent) {
    if (isCollection.value || props.hasPurgeOption) {
        deleteMenu.value?.show();
    } else {
        onDeleteItem();
    }
}

function onDeleteItem() {
    emit("delete");
}

function onDeleteItemRecursively() {
    const recursive = true;
    emit("delete", recursive);
}

function onDisplay($event: MouseEvent) {
    // Wrap display handler to allow ctrl/meta click to open in new tab
    // instead of triggering display.
    if ($event.ctrlKey || $event.metaKey) {
        window.open(displayUrl.value, "_blank");
    } else {
        emit("display");
    }
}
</script>

<template>
    <span class="align-self-start btn-group align-items-baseline">
        <!-- Special case for collections -->
        <BButton
            v-if="isCollection && canShowCollectionDetails"
            v-b-tooltip.hover
            class="collection-job-details-btn px-1"
            title="Show Details"
            size="sm"
            variant="link"
            :href="showCollectionDetailsUrl"
            @click.prevent.stop="emit('showCollectionInfo')">
            <icon icon="info-circle" />
        </BButton>
        <!-- Common for all content items -->
        <BButton
            v-if="isDataset"
            v-b-tooltip.hover
            :disabled="displayDisabled"
            :title="displayButtonTitle"
            tabindex="0"
            class="display-btn px-1"
            size="sm"
            variant="link"
            :href="displayUrl"
            @click.prevent.stop="onDisplay($event)">
            <icon icon="eye" />
        </BButton>
        <BButton
            v-if="writable && isHistoryItem"
            v-b-tooltip.hover
            :disabled="editDisabled"
            :title="editButtonTitle"
            tabindex="0"
            class="edit-btn px-1"
            size="sm"
            variant="link"
            :href="editUrl"
            @click.prevent.stop="emit('edit')">
            <icon icon="pen" />
        </BButton>
        <BButton
            v-if="writable && isHistoryItem && !isDeleted"
            v-b-tooltip.hover
            :tabindex="isDataset ? '0' : '-1'"
            class="delete-btn px-1"
            title="Delete"
            size="sm"
            variant="link"
            @click.stop="onDelete($event)">
            <icon v-if="isDataset && !props.hasPurgeOption" icon="trash" />
            <BDropdown v-else ref="deleteMenu" size="sm" variant="link" no-caret toggle-class="p-0 m-0">
                <template v-slot:button-content>
                    <icon icon="trash" />
                </template>
                <template v-if="isCollection">
                    <b-dropdown-item title="Delete collection only" @click.prevent.stop="onDeleteItem">
                        <icon icon="file" />
                        Collection only
                    </b-dropdown-item>
                    <b-dropdown-item
                        title="Delete collection and elements"
                        @click.prevent.stop="onDeleteItemRecursively">
                        <icon icon="copy" />
                        Collection and elements
                    </b-dropdown-item>
                </template>
                <template v-else-if="props.hasPurgeOption">
                    <b-dropdown-item title="Delete dataset" @click.prevent.stop="onDeleteItem">
                        <icon icon="trash" />
                        Delete dataset
                    </b-dropdown-item>
                    <b-dropdown-item title="Permanently delete dataset" @click.prevent.stop="emit('purge')">
                        <icon icon="burn" />
                        Permanently delete dataset
                    </b-dropdown-item>
                </template>
            </BDropdown>
        </BButton>
        <BButton
            v-if="writable && isHistoryItem && isDeleted"
            v-b-tooltip.hover
            tabindex="0"
            class="undelete-btn px-1"
            title="Undelete"
            size="sm"
            variant="link"
            @click.stop="emit('undelete')">
            <icon icon="trash-restore" />
        </BButton>
        <BButton
            v-if="writable && isHistoryItem && !isVisible"
            v-b-tooltip.hover
            tabindex="0"
            class="unhide-btn px-1"
            title="Unhide"
            size="sm"
            variant="link"
            @click.stop="emit('unhide')">
            <icon icon="eye-slash" />
        </BButton>
    </span>
</template>

<style lang="css">
.dropdown-menu .dropdown-item {
    font-weight: normal;
}
</style>
```
