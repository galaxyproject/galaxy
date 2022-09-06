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
            <span class="small text-black-50 mb-1">
                created on
                <UtcDate class="text-black-50 small mb-2" :date="item.create_time" mode="pretty" />
            </span>

            <b-button size="small" variant="outline-danger" @click="toggleDeleteModal">
                <icon icon="trash" />
                <span v-localize>Delete</span>
            </b-button>
        </b-row>

        <b-modal ref="modal" title="Delete API key" size="md" @ok="deleteKey">
            <p v-localize>Are you sure you want to delete this key?</p>
        </b-modal>
    </b-card>
</template>

<script>
import { mapGetters } from "vuex";
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
    computed: {
        ...mapGetters("user", ["currentUser"]),
    },
    methods: {
        toggleDeleteModal() {
            this.$refs.modal.toggle();
        },
        deleteKey() {
            svc.deleteAPIKey(this.currentUser.id, this.item.key)
                .then(() => this.$emit("listAPIKeys"))
                .catch((err) => (this.errorMessage = err.message));
        },
    },
};
</script>
