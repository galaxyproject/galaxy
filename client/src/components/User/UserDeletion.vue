<script setup lang="ts">
import { faExclamationTriangle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BFormGroup, BFormInput, BModal } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import { GalaxyApi, isRegisteredUser } from "@/api";
import { useUserStore } from "@/stores/userStore";
import { userLogoutClient } from "@/utils/logout";

const emit = defineEmits<{
    (e: "reset"): void;
}>();

const userStore = useUserStore();
const { currentUser } = storeToRefs(userStore);

const modal = ref();
const touched = ref(false);
const userInput = ref("");
const deleteError = ref("");

const userId = computed(() => (isRegisteredUser(currentUser.value) && currentUser.value?.id) || "");
const userEmail = computed(() => isRegisteredUser(currentUser.value) && currentUser.value?.email);
const inputState = computed(() => (touched.value ? nameState : null));
const nameState = computed(() => userInput.value === userEmail.value);
const showDeleteError = computed(() => {
    return deleteError.value !== "";
});

function resetModal() {
    userInput.value = "";
    emit("reset");
}

async function handleSubmit() {
    if (nameState.value) {
        const { error } = await GalaxyApi().DELETE("/api/users/{user_id}", {
            params: {
                path: {
                    user_id: userId.value,
                },
            },
        });

        if (error) {
            if (error.err_code === 403) {
                ("User deletion must be configured on this instance in order to allow user self-deletion.  Please contact an administrator for assistance.");
            } else {
                deleteError.value = "An error occurred while deleting the user.";
            }
        } else {
            userLogoutClient();
        }
    }
}
</script>

<template>
    <BModal
        id="modal-prevent-closing"
        ref="modal"
        centered
        title="Account Deletion"
        title-tag="h2"
        visible
        ok-variant="danger"
        ok-title="Delete Account Permanently"
        cancel-variant="outline-primary"
        :ok-disabled="!nameState"
        @hidden="resetModal"
        @ok="handleSubmit">
        <BAlert variant="danger" :show="showDeleteError">{{ deleteError }}</BAlert>
        <BAlert variant="warning" show>
            <b>
                <FontAwesomeIcon :icon="faExclamationTriangle" />
                This action cannot be undone. Your account will be PERMANENTLY deleted, along with the data contained in
                it.
            </b>
        </BAlert>

        <BFormGroup
            :state="inputState"
            label="Enter your email address to confirm deletion"
            invalid-feedback="Email does not match the current user email.">
            <BFormInput id="name-input" v-model="userInput" :state="inputState" required @blur="touched = true" />
        </BFormGroup>
    </BModal>
</template>
