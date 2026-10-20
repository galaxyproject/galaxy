<script setup lang="ts">
import { components } from "@/schema"

type Category = components["schemas"]["Category"]

defineProps<{ categories: Category[] }>()
</script>
<template>
    <h2 class="shed-section-title">Categories</h2>
    <ul class="repository-categories">
        <li v-for="category in categories" :key="category.id">
            <router-link class="repository-category" :to="`/repositories_by_category/${category.id}`">{{
                category.name
            }}</router-link>
        </li>
    </ul>
</template>

<style scoped>
.repository-categories {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin: 0;
    padding: 0;
    list-style: none;
}

.repository-category {
    display: inline-block;
    padding: 0.2rem 0.7rem;
    font-size: 0.85rem;
    color: var(--shed-link);
    text-decoration: none;
    background: var(--shed-page-bg);
    border: 1px solid var(--shed-border);
    border-radius: 999px;
}

.repository-category:hover {
    color: var(--shed-link-hover);
    border-color: var(--shed-link);
}
</style>
