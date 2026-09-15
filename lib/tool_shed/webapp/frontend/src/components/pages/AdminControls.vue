<script setup lang="ts">
import { computed, ref } from "vue"
import { storeToRefs } from "pinia"
import { ToolShedApi, components } from "@/schema"
import PageContainer from "@/components/PageContainer.vue"
import SelectUser from "@/components/SelectUser.vue"
import { AUTH_FORM_INPUT_PROPS } from "@/constants"
import { useUsersStore } from "@/stores"
import { notify, notifyOnCatch } from "@/util"

type IndexResults = components["schemas"]["BuildSearchIndexResponse"]

const searchResults = ref<IndexResults>()

const { users } = storeToRefs(useUsersStore())
const selectedUsername = ref<string | null>(null)
const password = ref("")
const confirm = ref("")

const selectedUserId = computed(() => users.value.find((user) => user.username === selectedUsername.value)?.id)

async function onIndex() {
    try {
        const { data } = await ToolShedApi().PUT("/api/tools/build_search_index")
        searchResults.value = data
    } catch (e) {
        notifyOnCatch(e)
    }
}

async function onResetPassword() {
    const encodedUserId = selectedUserId.value
    if (!encodedUserId) {
        notify("Select the user whose password you want to reset.")
        return
    }
    try {
        await ToolShedApi().PUT("/api/users/{encoded_user_id}/password", {
            params: { path: { encoded_user_id: encodedUserId } },
            body: {
                password: password.value,
                confirm: confirm.value,
            },
        })
        notify(`Password reset for ${selectedUsername.value}, their other sessions were logged out.`)
        password.value = ""
        confirm.value = ""
    } catch (e) {
        notifyOnCatch(e)
    }
}
</script>

<template>
    <page-container>
        <q-btn label="Re-index search" @click="onIndex" />
        <div v-if="searchResults">
            {{ searchResults }}
        </div>
        <q-separator class="q-my-lg" />
        <h6 class="q-my-md">Reset a user's password</h6>
        <q-form class="q-gutter-md" style="max-width: 30rem" action="#" @submit.prevent="onResetPassword">
            <select-user
                label="Select user"
                persist-selection
                @selected-user="selectedUsername = $event"
                @cleared="selectedUsername = null"
            />
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
            <q-btn unelevated color="primary" label="Reset Password" type="submit" name="reset_password_button" />
        </q-form>
    </page-container>
</template>
