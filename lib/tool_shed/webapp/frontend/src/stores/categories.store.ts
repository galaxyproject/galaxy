import { defineStore } from "pinia"

import { ToolShedApi, components } from "@/schema"
import { notifyOnCatch } from "@/util"
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
            try {
                const { data: categories } = await ToolShedApi().GET("/api/categories")
                this.categories = categories ?? []
            } catch (e) {
                notifyOnCatch(e)
            } finally {
                this.loading = false
            }
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
