<template>
    <span class="align-self-start btn-group">
        <!-- Special case for collections -->
        <b-button
            v-if="isCollection && canShowCollectionDetails"
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
            class="display-btn px-1"
            size="sm"
            variant="link"
            :href="displayUrl"
            @click.prevent.stop="$emit('display')">
            <icon icon="eye" />
        </b-button>
        <b-button
            v-if="isHistoryItem"
            :disabled="editDisabled"
            :title="editButtonTitle"
            class="edit-btn px-1"
            size="sm"
            variant="link"
            :href="editUrl"
            @click.prevent.stop="$emit('edit')">
            <icon icon="pen" />
        </b-button>
        <b-button
            v-if="isHistoryItem && !isDeleted"
            class="delete-btn px-1"
            title="Delete"
            size="sm"
            variant="link"
            @click.stop="$emit('delete')">
            <icon icon="trash" />
        </b-button>
        <b-button
            v-if="isHistoryItem && isDeleted"
            class="undelete-btn px-1"
            title="Undelete"
            size="sm"
            variant="link"
            @click.stop="$emit('undelete')">
            <icon icon="trash-restore" />
        </b-button>
        <b-button
            v-if="isHistoryItem && !isVisible"
            class="unhide-btn px-1"
            title="Unhide"
            size="sm"
            variant="link"
            @click.stop="$emit('unhide')">
            <icon icon="eye-slash" />
        </b-button>
    </span>
</template>

<script>
import { prependPath } from "utils/redirect.js";
export default {
    props: {
        isDataset: { type: Boolean, required: true },
        isDeleted: { type: Boolean, default: false },
        isHistoryItem: { type: Boolean, required: true },
        isVisible: { type: Boolean, default: true },
        state: { type: String, default: "" },
        itemUrls: { type: Object, required: true },
    },
    computed: {
        displayButtonTitle() {
            if (this.displayDisabled) {
                return "This dataset is not yet viewable.";
            }
            return "Display";
        },
        displayDisabled() {
            return ["discarded", "new", "upload"].includes(this.state);
        },
        editButtonTitle() {
            if (this.editDisabled) {
                return "This dataset is not yet editable.";
            }
            return "Edit attributes";
        },
        editDisabled() {
            return ["discarded", "new", "upload", "queued", "running", "waiting"].includes(this.state);
        },
        displayUrl() {
            return prependPath(this.itemUrls.display);
        },
        editUrl() {
            return prependPath(this.itemUrls.edit);
        },
        isCollection() {
            return !this.isDataset;
        },
        canShowCollectionDetails() {
            return !!this.itemUrls.showDetails;
        },
        showCollectionDetailsUrl() {
            return prependPath(this.itemUrls.showDetails);
        },
    },
};
</script>
