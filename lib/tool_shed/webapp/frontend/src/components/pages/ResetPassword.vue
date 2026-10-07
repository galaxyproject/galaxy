<script setup lang="ts">
import { ref } from "vue"
import { useRoute } from "vue-router"
import ModalForm from "@/components/ModalForm.vue"
import ErrorBanner from "@/components/ErrorBanner.vue"
import { AUTH_FORM_INPUT_PROPS } from "@/constants"
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
        <q-card-section>
            <error-banner v-if="error" :error="error" @dismiss="dismiss" />
            <q-form name="reset_password" class="q-gutter-md" action="#" @submit.prevent="onSubmit">
                <q-input
                    v-bind="AUTH_FORM_INPUT_PROPS"
                    v-model="password"
                    type="password"
                    label="New Password"
                    name="password"
                />
                <q-input
                    v-bind="AUTH_FORM_INPUT_PROPS"
                    v-model="confirm"
                    type="password"
                    label="Re-enter New Password"
                    name="confirm"
                />
                <q-btn
                    unelevated
                    color="primary"
                    size="lg"
                    class="full-width"
                    label="Set Password"
                    type="submit"
                    name="set_password_button"
                />
            </q-form>
        </q-card-section>
        <q-card-section class="text-center q-pa-none">
            <p class="text-grey-6">
                Link expired? <router-link to="/user/forgot_password">Request a new one.</router-link>
            </p>
        </q-card-section>
    </modal-form>
</template>
