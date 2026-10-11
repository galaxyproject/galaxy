<script setup lang="ts">
import { ref } from "vue"
import PageContainer from "@/components/PageContainer.vue"
import PageHeader from "@/components/PageHeader.vue"
import SelectUser from "@/components/SelectUser.vue"
import RepositoriesForOwner from "@/components/RepositoriesForOwner.vue"

interface RepositoriesByOwnerProps {
    username?: string | null
}

const props = withDefaults(defineProps<RepositoriesByOwnerProps>(), {
    username: null,
})

const username = ref<string | null>(props.username)

function onSelectUser(usernameStr: string) {
    username.value = usernameStr
}

function onCleared() {
    username.value = null
}
</script>
<template>
    <page-container>
        <template #header>
            <page-header
                :title="username ?? 'Owners'"
                :subtitle="username ? undefined : 'Pick a Tool Shed user to see the repositories they own.'"
            >
                <template v-if="username" #eyebrow>Owners</template>
            </page-header>
        </template>
        <div v-if="!props.username" class="owner-select-card shed-card">
            <select-user
                :persist-selection="true"
                label="Select user to browse owner properties"
                @selected-user="onSelectUser"
                @cleared="onCleared"
                class="owner-select"
                :dense="false"
            >
            </select-user>
        </div>
        <div v-if="username">
            <repositories-for-owner :key="username" :username="username" />
        </div>
    </page-container>
</template>

<style scoped>
.owner-select-card {
    margin-bottom: 1.5rem;
    padding: 1rem 1.25rem;
}
</style>
