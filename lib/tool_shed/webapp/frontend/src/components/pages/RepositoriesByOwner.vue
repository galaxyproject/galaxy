<script setup lang="ts">
import PageContainer from "@/components/PageContainer.vue"
import RepositoriesForOwner from "@/components/RepositoriesForOwner.vue"

interface RepositoriesByOwnerProps {
    username: string
}

defineProps<RepositoriesByOwnerProps>()
</script>
<template>
    <page-container>
        <repositories-for-owner :username="username" />
    </page-container>
</template>
