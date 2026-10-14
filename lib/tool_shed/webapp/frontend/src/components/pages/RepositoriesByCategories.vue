<script setup lang="ts">
import { GTable, type TableField } from "@galaxyproject/galaxy-ui"
import PageContainer from "@/components/PageContainer.vue"
import PageHeader from "@/components/PageHeader.vue"
import LoadingDiv from "@/components/LoadingDiv.vue"
import { computed } from "vue"
import { storeToRefs } from "pinia"
import { useCategoriesStore } from "@/stores"

const categoriesStore = useCategoriesStore()
const { loading, categories } = storeToRefs(categoriesStore)

const hidePackages = ["Tool Dependency Packages"]

const viewableCategories = computed(() => {
    return categories.value.filter((c) => hidePackages.indexOf(c.name) == -1)
})

const fields: TableField[] = [
    { key: "name", label: "Name", sortable: true },
    { key: "description", label: "Description" },
    { key: "repositories", label: "Repositories", align: "right", sortable: true },
]

void categoriesStore.getAll()
</script>
<template>
    <page-container>
        <template #header>
            <page-header title="Categories" subtitle="Browse repositories grouped by the kind of analysis they do." />
        </template>
        <LoadingDiv v-if="loading" message="Loading categories" />
        <GTable
            v-else
            id="categories"
            class="categories-table shed-table-card"
            :items="viewableCategories"
            :fields="fields"
            primary-key="id"
            sort-by="name"
        >
            <template #table-caption>
                <span class="shed-visually-hidden">Categories</span>
            </template>
            <template #cell(name)="{ item }">
                <router-link class="category-name" :to="`/repositories_by_category/${item.id}`">
                    {{ item.name }}
                </router-link>
            </template>
            <template #cell(repositories)="{ item }">
                <span class="category-count">{{ item.repositories }}</span>
            </template>
        </GTable>
    </page-container>
</template>

<style scoped>
.category-name {
    font-size: 1.05rem;
    font-weight: 700;
}

.category-count {
    display: inline-block;
    min-width: 2.25rem;
    padding: 0.05rem 0.6rem;
    font-size: 0.85rem;
    font-weight: 700;
    text-align: center;
    color: var(--color-bay-of-many-900, #25537b);
    background: var(--color-bay-of-many-100, #edf4fa);
    border: 1px solid var(--color-bay-of-many-200, #cde0f0);
    border-radius: 999px;
}
</style>
