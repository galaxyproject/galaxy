<script setup>
import { ref } from "vue";
import svc from "./model/service";
import { getGalaxyInstance } from "app";
import UtcDate from "components/UtcDate";
import CopyToClipboard from "components/CopyToClipboard";

defineProps({
    item: {
        type: Object,
        required: true,
    },
});

const emit = defineEmits(["getAPIKey"]);

const currentUserId = getGalaxyInstance().user.id;

const modal = ref(null);
const hover = ref(false);
const errorMessage = ref(null);

const toggleDeleteModal = () => {
    modal.value.toggle();
};
const deleteKey = () => {
    svc.deleteAPIKey(currentUserId)
        .then(() => emit("getAPIKey"))
        .catch((err) => (errorMessage.value = err.message));
};
</script>

<template>
    <b-card title="Current API key">
        <div class="d-flex justify-content-between w-100">
            <div class="w-100">
                <b-input-group
                    class="w-100"
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
                        <b-button title="Delete api key" @click="toggleDeleteModal">
                            <icon icon="trash" />
                        </b-button>
                    </b-input-group-append>
                </b-input-group>
                <span class="small text-black-50">
                    created on
                    <UtcDate class="text-black-50 small" :date="item.create_time" mode="pretty" />
                </span>
            </div>
        </div>

        <b-modal ref="modal" title="Delete API key" size="md" @ok="deleteKey">
            <p v-localize>Are you sure you want to delete this key?</p>
        </b-modal>
    </b-card>
</template>
