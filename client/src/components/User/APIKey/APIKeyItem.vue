<script setup lang="ts">
import { faEye, faEyeSlash, faKey, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { ref } from "vue";

import type { APIKeyModel } from "@/api/users";
import { getGalaxyInstance } from "@/app";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { errorMessageAsString } from "@/utils/simple-error";

import services from "./model/service";

import GCard from "@/components/Common/GCard.vue";
import CopyToClipboard from "@/components/CopyToClipboard.vue";
import UtcDate from "@/components/UtcDate.vue";

const props = defineProps<{
    item: APIKeyModel;
}>();

const emit = defineEmits(["getAPIKey"]);

const { confirm } = useConfirmDialog();

const currentUserId = getGalaxyInstance().user.id;

const hover = ref(false);
const errorMessage = ref<string | null>(null);

async function attemptKeyDeletion() {
    const confirmed = await confirm("Are you sure you want to delete this key?", {
        title: "Delete API key",
        okText: "Delete",
        okIcon: faTrash,
        okColor: "red",
    });

    if (confirmed) {
        try {
            await services.deleteAPIKey(currentUserId);
            errorMessage.value = null;
            emit("getAPIKey");
        } catch (e) {
            errorMessage.value = errorMessageAsString(e);
        }
    }
}
</script>

<template>
    <GCard title="Current API key" content-class="p-3">
        <template v-slot:description>
            <div class="d-flex justify-content-between w-100">
                <div class="w-100">
                    <b-input-group class="w-100">
                        <b-input-group-prepend>
                            <b-input-group-text>
                                <FontAwesomeIcon :icon="faKey" />
                            </b-input-group-text>
                        </b-input-group-prepend>

                        <b-input
                            :type="hover ? 'text' : 'password'"
                            :value="props.item.key"
                            disabled
                            data-test-id="api-key-input" />

                        <b-input-group-append>
                            <b-input-group-text>
                                <CopyToClipboard
                                    message="Key was copied to clipboard"
                                    :text="props.item.key"
                                    title="Copy key" />
                            </b-input-group-text>

                            <b-button v-g-tooltip.hover title="Show/hide key" @click="hover = !hover">
                                <FontAwesomeIcon :icon="hover ? faEyeSlash : faEye" />
                            </b-button>

                            <b-button title="Delete api key" @click="attemptKeyDeletion">
                                <FontAwesomeIcon :icon="faTrash" />
                            </b-button>
                        </b-input-group-append>
                    </b-input-group>
                    <span class="small text-black-50">
                        created on
                        <UtcDate class="text-black-50 small" :date="props.item.create_time" mode="pretty" />
                    </span>
                </div>
            </div>
        </template>
    </GCard>
</template>
