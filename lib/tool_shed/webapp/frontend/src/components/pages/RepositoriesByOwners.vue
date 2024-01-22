<script setup lang="ts">
import { ref } from "vue"
import PageContainer from "@/components/PageContainer.vue"
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
</script>
<template>
    <page-container>
        <select-user
            :persist-selection="true"
            label="Select user to browse owner properties"
            v-if="!props.username"
            @selected-user="onSelectUser"
            class="q-ma-md"
            :dense="false"
        >
        </select-user>
        <div v-if="username">
            <repositories-for-owner :key="username" :username="username" />
        </div>
    </page-container>
</template>
