<script setup lang="ts">
import axios from "axios";
import { BCard, BFormGroup, BFormInput } from "bootstrap-vue";
import { ref } from "vue";

import { SKIP_PENDING_REQUESTS_HEADER } from "@/api/pendingRequests";
import { discardActiveConnectionsBeforeAuthNavigation } from "@/composables/useAuthNavigation";
import { withPrefix } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";
import { uid } from "@/utils/utils";

import GAlert from "@/components/BaseComponents/GAlert.vue";
import GButton from "@/components/BaseComponents/GButton.vue";

interface Props {
    token?: string;
    expiredUser?: string;
    messageText?: string;
    messageVariant?: string;
}

const props = defineProps<Props>();

const fieldId = `change-password-${uid()}`;

const confirm = ref(null);
const current = ref(null);
const password = ref(null);
const message = ref(props.messageText);
const variant = ref(props.messageVariant);

async function submit() {
    // Changing the password logs the user in, so stop polling and abort
    // in-flight requests first; a late anonymous-cookie response could
    // otherwise overwrite the authenticated cookie we're about to receive.
    discardActiveConnectionsBeforeAuthNavigation();

    try {
        await axios.post(
            withPrefix("/user/change_password"),
            {
                token: props.token,
                id: props.expiredUser,
                current: current.value,
                password: password.value,
                confirm: confirm.value,
            },
            { headers: { [SKIP_PENDING_REQUESTS_HEADER]: "1" } },
        );

        // The server logs the user in; reload so the client picks up that session.
        window.location.replace(withPrefix("/"));
    } catch (error: any) {
        variant.value = "danger";
        message.value = errorMessageAsString(error, "Password change failed for an unknown reason.");
    }
}
</script>

<template>
    <form data-description="change password" @submit.prevent="submit">
        <GAlert v-if="!!message" :variant="variant" show>
            {{ message }}
        </GAlert>

        <BCard header="Change your password">
            <BFormGroup v-if="expiredUser" label="Current Password" :label-for="`${fieldId}-current`">
                <BFormInput
                    :id="`${fieldId}-current`"
                    v-model="current"
                    data-description="current password"
                    type="password"
                    autocomplete="current-password" />
            </BFormGroup>

            <BFormGroup label="New Password" :label-for="`${fieldId}-new`">
                <BFormInput
                    :id="`${fieldId}-new`"
                    v-model="password"
                    data-description="new password"
                    type="password"
                    autocomplete="new-password" />
            </BFormGroup>

            <BFormGroup label="Confirm password" :label-for="`${fieldId}-confirm`">
                <BFormInput
                    :id="`${fieldId}-confirm`"
                    v-model="confirm"
                    data-description="confirm password"
                    type="password"
                    autocomplete="new-password" />
            </BFormGroup>

            <GButton type="submit">Save new password</GButton>
        </BCard>
    </form>
</template>
