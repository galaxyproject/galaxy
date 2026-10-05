<script setup lang="ts">
import { ref, onMounted } from "vue"
import type { Repository } from "@/api"
import { errorMessageAsString } from "@/util"
import { recentlyCreatedRepositories } from "@/api"
import LoadingDiv from "@/components/LoadingDiv.vue"
import ErrorBanner from "@/components/ErrorBanner.vue"
import RepositoryCreation from "@/components/RepositoryCreation.vue"

const error = ref<string>()
const loading = ref(true)
const repositories = ref<Repository[]>()

onMounted(async () => {
    try {
        const repos = await recentlyCreatedRepositories()
        repositories.value = repos["hits"]
    } catch (e) {
        error.value = errorMessageAsString(e)
    } finally {
        loading.value = false
    }
})
</script>

<template>
    <div class="recently-created-repositories">
        <h2 class="recently-created-repositories-heading">Newest Repositories</h2>
        <error-banner :error="error" v-if="error" />
        <loading-div message="Loading most recently created repositories" v-else-if="loading" />
        <div v-else>
            <hr class="spaced" />
            <ul class="recently-created-repositories-list">
                <repository-creation v-for="repository of repositories" :key="repository.id" :repository="repository" />
            </ul>
        </div>
    </div>
</template>

<style scoped>
.recently-created-repositories {
    padding: var(--spacing-4);
    border: 1px solid var(--color-grey-300);
    border-radius: 0.25rem;
}

.recently-created-repositories-heading {
    margin: 0;
    color: var(--color-grey-600);
    font-size: var(--font-size-medium);
    font-weight: 600;
}

.recently-created-repositories-list {
    margin: 0;
    padding: 0;
    list-style: none;
}
</style>
