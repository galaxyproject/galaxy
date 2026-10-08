<script setup lang="ts">
import { ref } from "vue"
import ModalForm from "@/components/ModalForm.vue"
import { ToolShedApi } from "@/schema"
import { errorMessageAsString } from "@/util"
import ErrorBanner from "@/components/ErrorBanner.vue"
import { GButton, GForm, GFormInput, GFormLabel } from "@galaxyproject/galaxy-ui"
import router from "@/router"

const current = ref("")
const password = ref("")
const confirm = ref("")
const error = ref<string | null>(null)

async function onChange() {
    ToolShedApi()
        .PUT("/api_internal/change_password", {
            body: {
                current: current.value,
                password: password.value,
                confirm: confirm.value,
            },
        })
        .then(() => {
            router.push("/user/change_password_success")
        })
        .catch((e) => {
            error.value = errorMessageAsString(e)
        })
}

function dismiss() {
    error.value = null
}
</script>
<template>
    <modal-form title="Change Password">
        <div class="modal-form-section">
            <error-banner v-if="error" :error="error" @dismiss="dismiss" />
            <GForm class="change-password-form" action="#" @submit.prevent="onChange">
                <GFormLabel title="Current Password">
                    <GFormInput v-model="current" type="password" name="current" autocomplete="current-password" />
                </GFormLabel>
                <GFormLabel title="New Password">
                    <GFormInput v-model="password" type="password" name="password" autocomplete="new-password" />
                </GFormLabel>
                <GFormLabel title="Re-enter New Password">
                    <GFormInput v-model="confirm" type="password" name="confirm" autocomplete="new-password" />
                </GFormLabel>
                <GButton color="blue" size="large" class="submit-button" type="submit">Change Password</GButton>
            </GForm>
        </div>
    </modal-form>
</template>

<style scoped>
.change-password-form {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-4);
}

.submit-button {
    width: 100%;
}
</style>
