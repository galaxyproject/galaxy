<script setup lang="ts">
import { ref, watch } from "vue"
import RepositoryPage from "./RepositoryPage.vue"
import { ToolShedApi } from "@/schema"
import type { Repository } from "@/schema/types"
import LoadingDiv from "@/components/LoadingDiv.vue"
import ErrorBanner from "@/components/ErrorBanner.vue"
import { errorMessageAsString } from "@/util"

interface CitableRepositoryPageProps {
    username: string
    repositoryName: string
}
const props = defineProps<CitableRepositoryPageProps>()
const repositoryId = ref<string | null>(null)
const error = ref<string | null>(null)

async function update() {
    error.value = null
    try {
        const { data } = await ToolShedApi().GET("/api/repositories", {
            params: {
                query: {
                    owner: props.username,
                    name: props.repositoryName,
                },
            },
        })

        if (data instanceof Array) {
            if (data.length == 0) {
                error.value = `Repository ${props.username}/${props.repositoryName} is not found`
            } else {
                const repository: Repository = data[0]
                if (repository.id != repositoryId.value) {
                    repositoryId.value = repository.id
                }
            }
        }
    } catch (e) {
        error.value = errorMessageAsString(e)
    }
}

watch(props, async () => {
    await update()
})

update()
</script>
<template>
    <error-banner v-if="error" :error="error"> </error-banner>
    <repository-page :repository-id="repositoryId" v-else-if="repositoryId"> </repository-page>
    <loading-div v-else></loading-div>
</template>
