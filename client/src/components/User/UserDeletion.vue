<script setup lang="ts">
import { faExclamationTriangle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import { GalaxyApi, isRegisteredUser } from "@/api";
import { useUserStore } from "@/stores/userStore";
import { userLogoutClient } from "@/utils/logout";

import GForm from "../BaseComponents/Form/GForm.vue";
import GFormInput from "../BaseComponents/Form/GFormInput.vue";
import GFormLabel from "../BaseComponents/Form/GFormLabel.vue";
import GModal from "../BaseComponents/GModal.vue";
import LoadingSpan from "../LoadingSpan.vue";

const emit = defineEmits<{
    (e: "reset"): void;
}>();

const userStore = useUserStore();
const { currentUser } = storeToRefs(userStore);

const touched = ref(false);
const deleting = ref(false);
const userInput = ref("");
const deleteError = ref("");

const userId = computed(() => (isRegisteredUser(currentUser.value) && currentUser.value?.id) || "");
const userEmail = computed(() => isRegisteredUser(currentUser.value) && currentUser.value?.email);
const inputState = computed(() => (touched.value ? nameState.value : null));
const nameState = computed(() => userInput.value === userEmail.value);
const showDeleteError = computed(() => {
    return deleteError.value !== "";
});

function resetModal() {
    userInput.value = "";
    deleting.value = false;
    emit("reset");
}

async function handleSubmit() {
    if (nameState.value) {
        deleting.value = true;
        const { error } = await GalaxyApi().DELETE("/api/users/{user_id}", {
            params: {
                path: {
                    user_id: userId.value,
                },
            },
        });

        if (error) {
            if (error.err_code === 403) {
                deleteError.value =
                    "User deletion must be configured on this instance in order to allow user self-deletion.  Please contact an administrator for assistance.";
            } else {
                deleteError.value = "An error occurred while deleting the user.";
            }
            deleting.value = false;
        } else {
            userLogoutClient();
        }
    }
}
</script>

<template>
    <GModal
        id="modal-user-deletion"
        title="Account Deletion"
        show
        ok-color="red"
        ok-text="Delete Account Permanently"
        :ok-disabled="!nameState || deleting"
        ok-disabled-title="Please enter the correct email to enable account deletion"
        confirm
        :close-on-ok="false"
        @close="resetModal"
        @ok="handleSubmit">
        <BAlert variant="danger" :show="showDeleteError">{{ deleteError }}</BAlert>
        <BAlert variant="warning" show>
            <b>
                <FontAwesomeIcon :icon="faExclamationTriangle" />
                This action cannot be undone. Your account will be PERMANENTLY deleted, along with the data contained in
                it.
            </b>
        </BAlert>

        <BAlert v-if="deleting" variant="info" show>
            <LoadingSpan message="Deleting user account" />
        </BAlert>
        <GForm v-else @submit.native.prevent>
            <GFormLabel
                title="Enter your email address to confirm deletion"
                invalid-feedback="Email does not match the current user email."
                :state="inputState">
                <GFormInput
                    id="name-input"
                    v-model="userInput"
                    class="w-100"
                    :state="inputState"
                    type="email"
                    required
                    @blur="touched = true" />
            </GFormLabel>
        </GForm>
    </GModal>
</template>
