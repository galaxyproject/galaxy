<script setup lang="ts">
import { GButton, GForm, GFormInput, GFormLabel } from "@galaxyproject/galaxy-ui"
import { ref } from "vue"
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
    <GForm class="login-form" action="#" @submit.prevent="onLogin">
        <error-banner v-if="errorMessage" :error="errorMessage" @dismiss="errorMessage = null" />
        <GFormLabel title="Username / Email">
            <GFormInput
                :model-value="login"
                type="text"
                name="login"
                autocomplete="username"
                @update:model-value="login = $event ?? ''"
            />
        </GFormLabel>
        <GFormLabel title="Password">
            <GFormInput
                :model-value="password"
                type="password"
                name="password"
                autocomplete="current-password"
                @update:model-value="password = $event ?? ''"
            />
        </GFormLabel>
        <div class="login-form-actions">
            <GButton color="blue" size="large" class="submit-button" type="submit" name="login_button">Login</GButton>
        </div>
    </GForm>
</template>

<style scoped>
.login-form {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-4);
}

.login-form-actions {
    display: flex;
    align-items: center;
    padding: var(--spacing-2) var(--spacing-4);
}

.submit-button {
    width: 100%;
}
</style>
