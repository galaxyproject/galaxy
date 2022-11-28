<template>
    <span class="align-self-start btn-group">
        <b-button
            v-if="isDataset"
            :disabled="displayDisabled"
            :title="displayButtonTitle"
            class="display-btn px-1"
            size="sm"
            variant="link"
            :href="displayUrl"
            @click.prevent.stop="$emit('display')">
            <FontAwesomeIcon icon="fa-eye" />
        </b-button>
        <b-button
            v-if="writable && isHistoryItem"
            :disabled="editDisabled"
            :title="editButtonTitle"
            class="edit-btn px-1"
            size="sm"
            variant="link"
            :href="editUrl"
            @click.prevent.stop="$emit('edit')">
            <FontAwesomeIcon icon="fa-pen" />
        </b-button>
        <b-button
            v-if="writable && isHistoryItem && !isDeleted"
            class="delete-btn px-1"
            title="Delete"
            size="sm"
            variant="link"
            @click.stop="$emit('delete')">
            <FontAwesomeIcon icon="fa-trash" />
        </b-button>
        <b-button
            v-if="writable && isHistoryItem && isDeleted"
            class="undelete-btn px-1"
            title="Undelete"
            size="sm"
            variant="link"
            @click.stop="$emit('undelete')">
            <FontAwesomeIcon icon="fa-trash-restore" />
        </b-button>
        <b-button
            v-if="writable && isHistoryItem && !isVisible"
            class="unhide-btn px-1"
            title="Unhide"
            size="sm"
            variant="link"
            @click.stop="$emit('unhide')">
            <FontAwesomeIcon icon="fa-eye-slash" />
        </b-button>
    </span>
</template>

<script>
import { prependPath } from "utils/redirect.js";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faEye, faPen, faTrash, faTrashRestore, faEyeSlash } from "@fortawesome/free-solid-svg-icons";

library.add(faEye, faPen, faTrash, faTrashRestore, faEyeSlash);

export default {
    components: { FontAwesomeIcon },
    props: {
        writable: { type: Boolean, default: true },
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
            return ["discarded", "new", "upload", "queued"].includes(this.state);
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
    },
};
</script>
