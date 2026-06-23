<script setup lang="ts">
import PageContainer from "@/components/PageContainer.vue"
import { computed } from "vue"
import { storeToRefs } from "pinia"
import { useCategoriesStore } from "@/stores"

const categoriesStore = useCategoriesStore()
const { loading, categories } = storeToRefs(categoriesStore)

const hidePackages = ["Tool Dependency Packages"]

const viewableCategories = computed(() => {
    return categories.value.filter((c) => hidePackages.indexOf(c.name) == -1)
})

const columns = [
    { name: "name", label: "Name", field: "name", align: "left" as const, sortable: true },
    { name: "description", label: "Description", field: "description", align: "left" as const },
    { name: "repositories", label: "Repositories", field: "repositories", align: "right" as const, sortable: true },
]

void categoriesStore.getAll()
</script>
<template>
    <page-container>
        <h4 class="q-mt-none q-mb-md">Categories</h4>
        <div v-if="loading">
            <q-spinner />
        </div>
        <q-table
            v-else
            :rows="viewableCategories"
            :columns="columns"
            row-key="id"
            :pagination="{ rowsPerPage: 0 }"
            hide-pagination
            flat
            bordered
            aria-label="Categories"
            class="categories-table"
        >
            <template #header="props">
                <q-tr :props="props">
                    <q-th v-for="col in props.cols" :key="col.name" :props="props" class="table-header">
                        {{ col.label }}
                    </q-th>
                </q-tr>
            </template>
            <template #body-cell-name="props">
                <q-td :props="props" class="category-name-cell">
                    <router-link
                        class="text-primary text-weight-bold"
                        :to="`/repositories_by_category/${props.row.id}`"
                    >
                        {{ props.row.name }}
                    </router-link>
                </q-td>
            </template>
        </q-table>
    </page-container>
</template>

<style scoped>
.categories-table {
    font-size: 1.1rem;
}

.table-header {
    background-color: #f5f5f5;
    font-weight: 600;
    font-size: 1rem;
}

.category-name-cell {
    font-size: 1.2rem;
}
</style>
