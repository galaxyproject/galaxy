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

void categoriesStore.getAll()
</script>
<template>
    <page-container>
        <h4>Categories</h4>
        <div v-if="loading">
            <q-spinner />
        </div>
        <div class="row" style="max-width: 1200px">
            <div class="col-4" style="padding: 0.5em" v-for="category in viewableCategories" :key="category.id">
                <q-card>
                    <q-card-section>
                        <router-link
                            class="text-weight-bold text-primary"
                            :to="`/repositories_by_category/${category.id}`"
                            >{{ category.name }}</router-link
                        >
                    </q-card-section>
                    <q-separator />
                    <q-card-section class="text-right" style="color: gray">
                        {{ category.description }}
                        <br />
                        ({{ category.repositories }} repositories)
                    </q-card-section>
                </q-card>
            </div>
        </div>
    </page-container>
</template>
