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
    <div class="push-access" v-if="repository && repositoryPermissions">
        <h2 class="push-access-heading shed-section-title">Push access</h2>
        <p class="push-access-intro">Who can push to this repository?</p>
        <ul class="push-access-list">
            <li class="push-access-owner">{{ repository.owner }} (owner)</li>
            <li class="push-access-user" v-for="username in repositoryPermissions.allow_push" :key="username">
                <span class="push-access-username">{{ username }}</span>
                <GButton
                    class="push-access-remove"
                    icon-only
                    transparent
                    aria-label="Remove push access"
                    @click="removeUserAccess(username)"
                >
                    <FontAwesomeIcon :icon="faTrash" />
                </GButton>
            </li>
        </ul>
        <select-user @selected-user="addUserAccess" class="push-access-add"> </select-user>
    </div>
</template>

<style scoped>
.push-access-intro {
    margin: 0 0 0.5rem;
    font-size: 0.92rem;
    color: var(--shed-muted);
}

.push-access-list {
    margin: 0;
    padding: 0;
    list-style: none;
}

.push-access-owner,
.push-access-user {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    min-height: 2.25rem;
    padding: 0.25rem 0;
    font-weight: 700;
}

.push-access-user + .push-access-user,
.push-access-owner + .push-access-user {
    border-top: 1px solid var(--shed-border-subtle);
}

.push-access-add {
    display: block;
    margin-top: 0.75rem;
}
</style>
