<script setup lang="ts">
import { computed } from "vue"
import ConfigFileContents from "@/components/ConfigFileContents.vue"
import { UPDATING_WITH_PLANEMO_URL } from "@/constants"
import { components } from "@/schema"
import { shedYml } from "@/shedYml"

interface Props {
    repository: components["schemas"]["DetailedRepository"]
    categories: string[]
}

const props = defineProps<Props>()

const contents = computed(() => shedYml(props.repository, props.categories))
</script>

<template>
    <h2 class="shed-section-title">Planemo</h2>
    <p class="shed-yml-text">
        To manage this repository with <a :href="UPDATING_WITH_PLANEMO_URL">Planemo</a>, use a
        <code>.shed.yml</code> like:
    </p>
    <config-file-contents name=".shed.yml" :contents="contents" what=".shed.yml" />
</template>

<style scoped>
.shed-yml-text {
    margin: 0;
    font-size: 0.92rem;
}
</style>
