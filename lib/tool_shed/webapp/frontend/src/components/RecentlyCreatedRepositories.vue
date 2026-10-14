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
    <section class="recently-created-repositories shed-card">
        <h2 class="recently-created-repositories-heading">Newest repositories</h2>
        <div class="recently-created-repositories-body">
            <error-banner :error="error" v-if="error" />
            <loading-div message="Loading most recently created repositories" v-else-if="loading" />
            <ul v-else class="recently-created-repositories-list">
                <repository-creation v-for="repository of repositories" :key="repository.id" :repository="repository" />
            </ul>
        </div>
    </section>
</template>

<style scoped>
.recently-created-repositories {
    overflow: hidden;
}

.recently-created-repositories-heading {
    margin: 0;
    padding: 1rem 1.25rem 0.85rem;
    font-size: 1.05rem;
    font-weight: 700;
    border-bottom: 1px solid var(--shed-border-subtle);
}

.recently-created-repositories-list {
    margin: 0;
    padding: 0;
    list-style: none;
}
</style>
