<script setup lang="ts">
import { ref } from "vue"
import ModalForm from "@/components/ModalForm.vue"
import { AUTH_FORM_INPUT_PROPS } from "@/constants"
import { fetcher } from "@/schema"
import { errorMessage } from "@/util"
import ErrorBanner from "@/components/ErrorBanner.vue"
import router from "@/router"

const current = ref("")
const password = ref("")
const confirm = ref("")
const error = ref<string | null>(null)
const changePasswordFetcher = fetcher.path("/api_internal/change_password").method("put").create()

async function onChange() {
    changePasswordFetcher({
        current: current.value,
        password: password.value,
    })
        .then(() => {
            router.push("/")
        })
        .catch((e: Error) => {
            error.value = errorMessage(e)
        })
}

function dismiss() {
    error.value = null
}
</script>
<template>
    <modal-form title="Change Password">
        <q-card-section>
            <error-banner v-if="error" :error="error" @dismiss="dismiss" />
            <q-form class="q-gutter-md" action="#" @submit.prevent="onChange">
                <q-input v-bind="AUTH_FORM_INPUT_PROPS" v-model="current" type="password" label="Current Password" />
                <q-input v-bind="AUTH_FORM_INPUT_PROPS" v-model="password" type="password" label="New Password" />
                <q-input
                    v-bind="AUTH_FORM_INPUT_PROPS"
                    v-model="confirm"
                    type="password"
                    label="Re-enter New Password"
                />
                <q-btn unelevated color="primary" size="lg" class="full-width" label="Change Password" type="submit" />
            </q-form>
        </q-card-section>
    </modal-form>
</template>
