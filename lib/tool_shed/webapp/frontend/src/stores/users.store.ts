import { defineStore } from "pinia"

import { fetcher, components } from "@/schema"
const usersFetcher = fetcher.path("/api/users").method("get").create()

type User = components["schemas"]["UserV2"]

export const useUsersStore = defineStore({
    id: "users",
    state: () => ({
        users: [] as User[],
        loading: true,
    }),
    actions: {
        async getAll() {
            this.loading = true
            const { data: users } = await usersFetcher({})
            this.users = users
            this.loading = false
        },
    },
})
