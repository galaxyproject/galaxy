<script setup lang="ts">
import { ref } from "vue"
import { AUTH_FORM_INPUT_PROPS } from "@/constants"
import { useAuthStore } from "@/stores"
import { errorMessageAsString } from "@/util"
import ErrorBanner from "@/components/ErrorBanner.vue"

interface LoginFormProps {
    initialLogin?: string | null
}

const props = withDefaults(defineProps<LoginFormProps>(), {
    initialLogin: null,
})

const login = ref(props.initialLogin || "")
const password = ref("")
const errorMessage = ref<string | null>(null)

async function onLogin() {
    errorMessage.value = null
    const authStore = useAuthStore()
    try {
        await authStore.login(login.value, password.value)
    } catch (e) {
        errorMessage.value = errorMessageAsString(e)
    }
}
</script>
<template>
    <q-form class="q-gutter-md" action="#" @submit.prevent="onLogin">
        <error-banner v-if="errorMessage" :error="errorMessage" @dismiss="errorMessage = null" />
        <q-input v-bind="AUTH_FORM_INPUT_PROPS" v-model="login" type="text" label="Username / Email" name="login" />
        <q-input v-bind="AUTH_FORM_INPUT_PROPS" v-model="password" type="password" label="Password" name="password" />
        <q-card-actions class="q-px-md">
            <q-btn
                unelevated
                color="primary"
                size="lg"
                class="full-width"
                label="Login"
                type="submit"
                name="login_button"
            />
        </q-card-actions>
    </q-form>
</template>
