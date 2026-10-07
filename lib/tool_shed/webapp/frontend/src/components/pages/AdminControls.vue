<script setup lang="ts">
import { GButton, GForm, GFormInput, GFormLabel } from "@galaxyproject/galaxy-ui"
import { computed, ref } from "vue"
import { storeToRefs } from "pinia"
import { ToolShedApi, components } from "@/schema"
import PageContainer from "@/components/PageContainer.vue"
import PageHeader from "@/components/PageHeader.vue"
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
        <template #header>
            <page-header title="Admin controls" subtitle="Maintenance tasks for this Tool Shed." />
        </template>
        <div class="admin-grid">
            <section class="admin-card shed-card">
                <h2 class="shed-section-title">Search index</h2>
                <p class="admin-card-text">Rebuild the repository and tool search index from the current database.</p>
                <GButton color="blue" @click="onIndex">Re-index search</GButton>
                <pre v-if="searchResults" class="admin-results">{{ searchResults }}</pre>
            </section>
            <section class="admin-card shed-card">
                <h2 class="reset-password-heading shed-section-title">Reset a user's password</h2>
                <GForm class="reset-password-form" action="#" @submit.prevent="onResetPassword">
                    <select-user
                        label="Select user"
                        persist-selection
                        @selected-user="selectedUsername = $event"
                        @cleared="selectedUsername = null"
                    />
                    <GFormLabel title="New Password">
                        <GFormInput v-model="password" type="password" name="password" autocomplete="new-password" />
                    </GFormLabel>
                    <GFormLabel title="Re-enter New Password">
                        <GFormInput v-model="confirm" type="password" name="confirm" autocomplete="new-password" />
                    </GFormLabel>
                    <div>
                        <GButton color="blue" type="submit" name="reset_password_button">Reset Password</GButton>
                    </div>
                </GForm>
            </section>
        </div>
    </page-container>
</template>

<style scoped>
.admin-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 24rem), 1fr));
    gap: 1.25rem;
    align-items: start;
}

.admin-card {
    padding: 1.5rem;
}

.admin-card-text {
    margin: 0 0 1rem;
    color: var(--shed-muted);
}

.admin-results {
    margin: 1rem 0 0;
    padding: 0.75rem 1rem;
    font-size: 0.85rem;
    white-space: pre-wrap;
    background: color-mix(in srgb, var(--shed-page-bg) 60%, white);
    border: 1px solid var(--shed-border-subtle);
    border-radius: var(--shed-radius-sm);
}

.reset-password-form {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}
</style>
