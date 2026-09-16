<script setup lang="ts">
import { useRepositoryStore } from "@/stores"
import { storeToRefs } from "pinia"
import SelectUser from "@/components/SelectUser.vue"

const repositoryStore = useRepositoryStore()
const { repository, repositoryPermissions } = storeToRefs(repositoryStore)

interface ManagePushAccessProps {
    repositoryId: string
}

defineProps<ManagePushAccessProps>()

function addUserAccess(username: string) {
    return repositoryStore.allowPush(username)
}

function removeUserAccess(username: string) {
    return repositoryStore.disallowPush(username)
}
</script>
<template>
    <q-list
        bordered
        padding
        class="rounded-borders"
        style="max-width: 325px"
        v-if="repository && repositoryPermissions"
    >
        <q-item-label header>Who can push to this repository?</q-item-label>
        <q-item>
            <q-item-section>
                <q-item-label>{{ repository.owner }} (owner)</q-item-label>
            </q-item-section>
        </q-item>
        <q-item v-for="username in repositoryPermissions.allow_push" :key="username">
            <q-item-section>
                <q-item-label>{{ username }}</q-item-label>
            </q-item-section>
            <q-item-section avatar>
                <q-icon name="delete" @click="removeUserAccess(username)" />
            </q-item-section>
        </q-item>
        <select-user @selected-user="addUserAccess" class="q-ma-md"> </select-user>
    </q-list>
</template>
