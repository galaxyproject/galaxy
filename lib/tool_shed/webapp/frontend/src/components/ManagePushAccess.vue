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
        <h3 class="push-access-heading">Who can push to this repository?</h3>
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
.push-access {
    max-width: 325px;
    padding: var(--spacing-3);
    border: 1px solid var(--color-grey-300);
    border-radius: 0.25rem;
}

.push-access-heading {
    margin: 0 0 var(--spacing-2);
    color: var(--color-grey-600);
    font-size: var(--font-size-medium);
    font-weight: 600;
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
    gap: var(--spacing-2);
    padding: var(--spacing-2) 0;
}

.push-access-add {
    display: block;
    margin-top: var(--spacing-4);
}
</style>
