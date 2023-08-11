<script setup>
import { getGalaxyInstance } from "app";
import CopyToClipboard from "components/CopyToClipboard";
import UtcDate from "components/UtcDate";
import { ref } from "vue";

import {
    GButton,
    GCard,
    GInput,
    GInputGroup,
    GInputGroupAppend,
    GInputGroupPrepend,
    GInputGroupText,
    GModal,
} from "@/component-library";

import svc from "./model/service";

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
    <GCard title="Current API key">
        <div class="d-flex justify-content-between w-100">
            <div class="w-100">
                <GInputGroup
                    class="w-100"
                    @blur="hover = false"
                    @focus="hover = true"
                    @mouseover="hover = true"
                    @mouseleave="hover = false">
                    <GInputGroupPrepend>
                        <GInputGroupText>
                            <icon icon="key" />
                        </GInputGroupText>
                    </GInputGroupPrepend>

                    <GInput
                        :type="hover ? 'text' : 'password'"
                        :value="item.key"
                        disabled
                        data-test-id="api-key-input" />

                    <GInputGroupAppend>
                        <GInputGroupText>
                            <CopyToClipboard message="Key was copied to clipboard" :text="item.key" title="Copy key" />
                        </GInputGroupText>
                        <GButton title="Delete api key" @click="toggleDeleteModal">
                            <icon icon="trash" />
                        </GButton>
                    </GInputGroupAppend>
                </GInputGroup>
                <span class="small text-black-50">
                    created on
                    <UtcDate class="text-black-50 small" :date="item.create_time" mode="pretty" />
                </span>
            </div>
        </div>

        <GModal ref="modal" title="Delete API key" size="md" @ok="deleteKey">
            <p v-localize>Are you sure you want to delete this key?</p>
        </GModal>
    </GCard>
</template>
