import { defineStore } from "pinia"

import { ToolShedApi, components } from "@/schema"

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
            const { data: users } = await ToolShedApi().GET("/api/users")
            this.users = users ?? []
            this.loading = false
        },
    },
})
