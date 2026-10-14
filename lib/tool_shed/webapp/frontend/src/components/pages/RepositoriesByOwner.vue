<script setup lang="ts">
import PageContainer from "@/components/PageContainer.vue"
import PageHeader from "@/components/PageHeader.vue"
import RepositoriesForOwner from "@/components/RepositoriesForOwner.vue"

interface RepositoriesByOwnerProps {
    username: string
}

defineProps<RepositoriesByOwnerProps>()
</script>
<template>
    <page-container>
        <template #header>
            <page-header :title="username">
                <template #eyebrow><router-link to="/repositories_by_owner">Owners</router-link></template>
            </page-header>
        </template>
        <repositories-for-owner :username="username" />
    </page-container>
</template>
