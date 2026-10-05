<script setup lang="ts">
import { GTable, type TableField } from "@galaxyproject/galaxy-ui"
import PageContainer from "@/components/PageContainer.vue"
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
        <h1 class="categories-heading">Categories</h1>
        <LoadingDiv v-if="loading" message="Loading categories" />
        <GTable
            v-else
            id="categories"
            class="categories-table"
            :items="viewableCategories"
            :fields="fields"
            primary-key="id"
            sort-by="name"
            bordered
        >
            <template #table-caption>
                <span class="visually-hidden">Categories</span>
            </template>
            <template #cell(name)="{ item }">
                <router-link class="category-name" :to="`/repositories_by_category/${item.id}`">
                    {{ item.name }}
                </router-link>
            </template>
        </GTable>
    </page-container>
</template>

<style scoped>
.categories-table {
    font-size: 1.1rem;
}

.categories-heading {
    margin: 0 0 var(--spacing-4);
    font-size: 2.125rem;
}

.category-name {
    font-size: 1.2rem;
    font-weight: bold;
    color: var(--color-galaxy-primary);
}

/* The heading above already says "Categories"; the caption names the table for assistive tech */
.visually-hidden {
    position: absolute;
    width: 1px;
    height: 1px;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
}
</style>
