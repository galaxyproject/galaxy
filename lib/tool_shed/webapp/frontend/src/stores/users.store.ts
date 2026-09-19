import { defineStore } from "pinia"

import { ToolShedApi, components } from "@/schema"
import { notifyOnCatch } from "@/util"

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
            try {
                const { data: users } = await ToolShedApi().GET("/api/users")
                this.users = users ?? []
            } catch (e) {
                notifyOnCatch(e)
            } finally {
                this.loading = false
            }
        },
    },
})
