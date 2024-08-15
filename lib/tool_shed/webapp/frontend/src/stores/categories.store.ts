import { defineStore } from "pinia"

import { fetcher, components } from "@/schema"
const categoriesFetcher = fetcher.path("/api/categories").method("get").create()
type Category = components["schemas"]["Category"]

export const useCategoriesStore = defineStore({
    id: "categories",
    state: () => ({
        categories: [] as Category[],
        loading: true,
    }),
    actions: {
        async getAll() {
            this.loading = true
            const { data: categories } = await categoriesFetcher({})
            this.categories = categories
            this.loading = false
        },
    },
    getters: {
        byId(state) {
            return (categoryId: string) => {
                for (const category of state.categories) {
                    if (category.id == categoryId) {
                        return category
                    }
                }
                return null
            }
        },
    },
})
