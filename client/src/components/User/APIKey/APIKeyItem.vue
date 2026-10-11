<script setup lang="ts">
import { faEye, faEyeSlash, faKey, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BFormInput, BInputGroup, BInputGroupAppend, BInputGroupPrepend, BInputGroupText } from "bootstrap-vue";
import { ref } from "vue";

import type { APIKeyModel } from "@/api/users";
import { getGalaxyInstance } from "@/app";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { errorMessageAsString } from "@/utils/simple-error";

import services from "./model/service";

import GButton from "@/components/BaseComponents/GButton.vue";
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
                    <BInputGroup class="w-100">
                        <BInputGroupPrepend>
                            <BInputGroupText>
                                <FontAwesomeIcon :icon="faKey" />
                            </BInputGroupText>
                        </BInputGroupPrepend>

                        <BFormInput
                            :type="hover ? 'text' : 'password'"
                            :value="props.item.key"
                            disabled
                            data-test-id="api-key-input" />

                        <BInputGroupAppend>
                            <BInputGroupText>
                                <CopyToClipboard
                                    message="Key was copied to clipboard"
                                    :text="props.item.key"
                                    title="Copy key" />
                            </BInputGroupText>

                            <GButton v-g-tooltip.hover title="Show/hide key" icon-only @click="hover = !hover">
                                <FontAwesomeIcon :icon="hover ? faEyeSlash : faEye" />
                            </GButton>

                            <GButton title="Delete api key" icon-only @click="attemptKeyDeletion">
                                <FontAwesomeIcon :icon="faTrash" />
                            </GButton>
                        </BInputGroupAppend>
                    </BInputGroup>
                    <span class="small text-black-50">
                        created on
                        <UtcDate class="text-black-50 small" :date="props.item.create_time" mode="pretty" />
                    </span>
                </div>
            </div>
        </template>
    </GCard>
</template>
