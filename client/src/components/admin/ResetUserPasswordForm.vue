<script setup lang="ts">
import { faSave } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { ref } from "vue";
import { useRouter } from "vue-router/composables";

import { GalaxyApi } from "@/api";
import { errorMessageAsString } from "@/utils/simple-error";

import GFormInput from "@/components/BaseComponents/Form/GFormInput.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import FormCard from "@/components/Form/FormCard.vue";
import FormElementLabel from "@/components/Form/FormElementLabel.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const props = defineProps<{
    userId: string;
}>();

const errorMessage = ref("");
const loading = ref(false);
const loadFailed = ref(false);
const email = ref("");
const password = ref("");
const confirm = ref("");

const router = useRouter();

async function loadUser() {
    loading.value = true;
    const { data, error } = await GalaxyApi().GET("/api/users/{user_id}", {
        params: { path: { user_id: props.userId } },
    });
    if (error) {
        errorMessage.value = errorMessageAsString(error);
        loadFailed.value = true;
    } else {
        email.value = "email" in data ? data.email : "";
    }
    loading.value = false;
}

async function onSubmit() {
    if (!password.value) {
        errorMessage.value = "Please enter a new password.";
        return;
    }
    if (password.value !== confirm.value) {
        errorMessage.value = "Passwords do not match.";
        return;
    }
    const { error } = await GalaxyApi().PUT("/api/users/{user_id}/password", {
        params: { path: { user_id: props.userId } },
        body: { password: password.value },
    });
    if (error) {
        errorMessage.value = errorMessageAsString(error);
        return;
    }
    router.push(`/admin/users?message=${encodeURIComponent(`Password reset for ${email.value}.`)}`);
}

loadUser();
</script>

<template>
    <div>
        <LoadingSpan v-if="loading" />
        <div v-else id="admin-reset-password-form">
            <GAlert v-if="errorMessage" variant="danger" show>{{ errorMessage }}</GAlert>
            <template v-if="!loadFailed">
                <FormCard :title="`Reset password for '${email}'`" icon="fa-user">
                    <template v-slot:body>
                        <FormElementLabel title="New password" :required="true" :condition="!!password">
                            <GFormInput
                                id="admin-reset-password"
                                v-model="password"
                                type="password"
                                autocomplete="new-password" />
                        </FormElementLabel>
                        <FormElementLabel title="Confirm password" :required="true" :condition="!!confirm">
                            <GFormInput
                                id="admin-reset-password-confirm"
                                v-model="confirm"
                                type="password"
                                autocomplete="new-password" />
                        </FormElementLabel>
                    </template>
                </FormCard>
                <GButton id="admin-reset-password-submit" class="my-2" color="blue" @click="onSubmit">
                    <FontAwesomeIcon :icon="faSave" class="mr-1" />
                    <span v-localize>Save new password</span>
                </GButton>
            </template>
        </div>
    </div>
</template>
