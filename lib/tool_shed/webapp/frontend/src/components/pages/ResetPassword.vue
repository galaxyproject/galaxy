<script setup lang="ts">
import { GButton, GForm, GFormInput, GFormLabel } from "@galaxyproject/galaxy-ui"
import { ref } from "vue"
import { useRoute } from "vue-router"
import ModalForm from "@/components/ModalForm.vue"
import ErrorBanner from "@/components/ErrorBanner.vue"
import { ToolShedApi } from "@/schema"
import { errorMessageAsString, queryParamToString } from "@/util"
import router from "@/router"

const token = queryParamToString(useRoute().query.token)
if (token) {
    // Remove the credential from browser history and subsequent referrers.
    router.replace({ query: {} })
}
const password = ref("")
const confirm = ref("")
const error = ref<string | null>(null)

async function onSubmit() {
    error.value = null
    if (!token) {
        error.value = "This password reset link is missing its token, please request a new one."
        return
    }
    try {
        await ToolShedApi().PUT("/api_internal/change_password", {
            body: {
                token: token,
                password: password.value,
                confirm: confirm.value,
            },
        })
        router.push("/user/change_password_success")
    } catch (e) {
        error.value = errorMessageAsString(e)
    }
}

function dismiss() {
    error.value = null
}
</script>

<template>
    <modal-form title="Choose a New Password">
        <div class="modal-form-section">
            <error-banner v-if="error" :error="error" @dismiss="dismiss" />
            <GForm name="reset_password" class="reset-password-form" action="#" @submit.prevent="onSubmit">
                <GFormLabel title="New Password">
                    <GFormInput
                        :model-value="password"
                        type="password"
                        name="password"
                        autocomplete="new-password"
                        @update:model-value="password = $event ?? ''"
                    />
                </GFormLabel>
                <GFormLabel title="Re-enter New Password">
                    <GFormInput
                        :model-value="confirm"
                        type="password"
                        name="confirm"
                        autocomplete="new-password"
                        @update:model-value="confirm = $event ?? ''"
                    />
                </GFormLabel>
                <GButton color="blue" size="large" class="submit-button" type="submit" name="set_password_button"
                    >Set Password</GButton
                >
            </GForm>
        </div>
        <div class="modal-form-section modal-form-section-footer">
            <p class="modal-form-footer-text">
                Link expired? <router-link to="/user/forgot_password">Request a new one.</router-link>
            </p>
        </div>
    </modal-form>
</template>

<style scoped>
.reset-password-form {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-4);
}

.submit-button {
    width: 100%;
}
</style>
