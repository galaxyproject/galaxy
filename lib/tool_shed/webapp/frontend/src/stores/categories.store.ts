import { defineStore } from "pinia"

import { client, components } from "@/schema"
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
            const { data: categories } = await client.GET("/api/categories")
            this.categories = categories ?? []
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
