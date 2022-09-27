<template>
    <b-card title="Galaxy API key">
        <div class="d-flex justify-content-between">
            <div>
                <b-input-group
                    @blur="hover = false"
                    @focus="hover = true"
                    @mouseover="hover = true"
                    @mouseleave="hover = false">
                    <b-input-group-prepend>
                        <b-input-group-text>
                            <icon icon="key" />
                        </b-input-group-text>
                    </b-input-group-prepend>

                    <b-input
                        :type="hover ? 'text' : 'password'"
                        :value="item.key"
                        disabled
                        data-test-id="api-key-input" />

                    <b-input-group-append>
                        <b-input-group-text>
                            <copy-to-clipboard
                                message="Key was copied to clipboard"
                                :text="item.key"
                                title="Copy key" />
                        </b-input-group-text>
                    </b-input-group-append>
                </b-input-group>
                <span class="small text-black-50">
                    created on
                    <UtcDate class="text-black-50 small" :date="item.create_time" mode="pretty" />
                </span>
            </div>

            <div class="h-100 ml-2">
                <b-button class="h-100" size="small" variant="outline-danger" @click="toggleDeleteModal">
                    <icon icon="trash" />
                    <span v-localize>Delete</span>
                </b-button>
            </div>
        </div>

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
            svc.deleteAPIKey(this.currentUser.id)
                .then(() => this.$emit("getAPIKey"))
                .catch((err) => (this.errorMessage = err.message));
        },
    },
};
</script>
