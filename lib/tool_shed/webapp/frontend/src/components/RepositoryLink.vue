<script setup lang="ts">
import { computed } from "vue"

interface RepositoryLinkProps {
    id: string
    name: string
    owner: string
}

const props = defineProps<RepositoryLinkProps>()

const repositoryTo = computed(() => `/repositories/${props.id}`)
</script>
<template>
    <router-link :to="repositoryTo" class="repository-link">
        <span class="owner">{{ owner }}</span
        >/<span class="name">{{ name }}</span>
    </router-link>
</template>

<style scoped>
.repository-link {
    color: var(--color-galaxy-primary);
}

.name {
    font-size: 1.2em;
    font-weight: bold;
}
</style>
