<script setup lang="ts">
import { ref } from "vue"
import { AUTH_FORM_INPUT_PROPS } from "@/constants"
import { useAuthStore } from "@/stores"

interface LoginFormProps {
    initialLogin?: string | null
}

const props = withDefaults(defineProps<LoginFormProps>(), {
    initialLogin: null,
})

const login = ref(props.initialLogin || "")
const password = ref("")

async function onLogin() {
    const authStore = useAuthStore()
    return authStore.login(login.value, password.value)
}
</script>
<template>
    <q-form class="q-gutter-md" action="#" @submit.prevent="onLogin">
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
