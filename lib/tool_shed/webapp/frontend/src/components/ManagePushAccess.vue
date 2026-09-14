<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { faTrash } from "@fortawesome/free-solid-svg-icons"
import { GButton } from "@galaxyproject/galaxy-ui"
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
        class="rounded-borders push-access"
        style="max-width: 325px"
        v-if="repository && repositoryPermissions"
    >
        <q-item-label header>Who can push to this repository?</q-item-label>
        <q-item class="push-access-owner">
            <q-item-section>
                <q-item-label>{{ repository.owner }} (owner)</q-item-label>
            </q-item-section>
        </q-item>
        <q-item class="push-access-user" v-for="username in repositoryPermissions.allow_push" :key="username">
            <q-item-section>
                <q-item-label class="push-access-username">{{ username }}</q-item-label>
            </q-item-section>
            <q-item-section avatar>
                <GButton
                    class="push-access-remove"
                    icon-only
                    transparent
                    aria-label="Remove push access"
                    @click="removeUserAccess(username)"
                >
                    <FontAwesomeIcon :icon="faTrash" />
                </GButton>
            </q-item-section>
        </q-item>
        <select-user @selected-user="addUserAccess" class="q-ma-md push-access-add"> </select-user>
    </q-list>
</template>
