<template>
    <span class="align-self-start btn-group">
        <b-button
            v-if="isDataset"
            :disabled="displayDisabled"
            :title="displayButtonTitle"
            class="px-1"
            size="sm"
            variant="link"
            @click.stop="$emit('display')">
            <icon icon="eye" />
        </b-button>
        <b-button
            v-if="isHistoryItem"
            :disabled="editDisabled"
            :title="editButtonTitle"
            class="px-1"
            size="sm"
            variant="link"
            @click.stop="$emit('edit')">
            <icon icon="pen" />
        </b-button>
        <b-button
            v-if="isHistoryItem && !isDeleted"
            class="px-1"
            title="Delete"
            size="sm"
            variant="link"
            @click.stop="$emit('delete')">
            <icon icon="trash" />
        </b-button>
        <b-button
            v-if="isHistoryItem && isDeleted"
            class="px-1"
            title="Undelete"
            size="sm"
            variant="link"
            @click.stop="$emit('undelete')">
            <icon icon="trash-restore" />
        </b-button>
        <b-button
            v-if="isHistoryItem && !isVisible"
            class="px-1"
            title="Unhide"
            size="sm"
            variant="link"
            @click.stop="$emit('unhide')">
            <icon icon="eye-slash" />
        </b-button>
    </span>
</template>

<script>
export default {
    props: {
        isDataset: { type: Boolean, required: true },
        isDeleted: { type: Boolean, default: false },
        isHistoryItem: { type: Boolean, required: true },
        isVisible: { type: Boolean, default: true },
        state: { type: String, default: "" },
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
    },
};
</script>
