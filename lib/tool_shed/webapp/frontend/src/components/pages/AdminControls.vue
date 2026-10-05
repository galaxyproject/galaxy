<script setup lang="ts">
import { GButton, GForm, GFormInput, GFormLabel } from "@galaxyproject/galaxy-ui"
import { computed, ref } from "vue"
import { storeToRefs } from "pinia"
import { ToolShedApi, components } from "@/schema"
import PageContainer from "@/components/PageContainer.vue"
import SelectUser from "@/components/SelectUser.vue"
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
        <GButton @click="onIndex">Re-index search</GButton>
        <div v-if="searchResults">
            {{ searchResults }}
        </div>
        <hr class="q-my-lg" />
        <h6 class="q-my-md">Reset a user's password</h6>
        <GForm class="reset-password-form" style="max-width: 30rem" action="#" @submit.prevent="onResetPassword">
            <select-user
                label="Select user"
                persist-selection
                @selected-user="selectedUsername = $event"
                @cleared="selectedUsername = null"
            />
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
            <GButton color="blue" type="submit" name="reset_password_button">Reset Password</GButton>
        </GForm>
    </page-container>
</template>

<style scoped>
.reset-password-form {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-4);
}
</style>
