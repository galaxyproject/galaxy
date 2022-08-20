<template>
    <b-card class="text-center">
        <b-input-group class="mb-2" @mouseover="hover = true" @mouseleave="hover = false">
            <b-input-group-prepend>
                <b-input-group-text>
                    <icon icon="key" />
                </b-input-group-text>
            </b-input-group-prepend>

            <b-input :type="hover ? 'text' : 'password'" :value="item.key" disabled />

            <b-input-group-append>
                <b-input-group-text>
                    <copy-to-clipboard message="Key was copied to clipboard" :text="item.key" title="Copy key" />
                </b-input-group-text>
            </b-input-group-append>
        </b-input-group>

        <b-row class="flex-column align-items-center">
            <UtcDate class="text-black-50 small mb-2" :date="item.create_time" mode="pretty" />

            <b-button size="small" variant="outline-danger" @click="toggleDeleteModal">Delete</b-button>
        </b-row>

        <b-modal ref="modal" title="Delete API key" size="md" @ok="deleteKey">
            <p v-localize>Are you sure you want to delete this key?</p>
        </b-modal>
    </b-card>
</template>

<script>
import svc from "./model/service";
import UtcDate from "components/UtcDate";
import CopyToClipboard from "components/CopyToClipboard";

export default {
    components: {
        UtcDate,
        CopyToClipboard,
    },
    props: {
        item: {
            type: Object,
            required: true,
        },
    },
    data() {
        return {
            hover: false,
            type: "password",
            showModal: false,
        };
    },
    methods: {
        toggleDeleteModal() {
            this.$refs.modal.toggle();
        },
        deleteKey() {
            svc.deleteAPIKey(this.item.key)
                .then(() => this.$emit("listAPIKeys"))
                .catch((err) => (this.errorMessage = err.message));
        },
    },
};
</script>
