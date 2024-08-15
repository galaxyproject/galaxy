import { defineStore } from "pinia"
import { ensureCookie, errorMessageAsString, notifyOnCatch } from "@/util"

import { ToolShedApi } from "@/schema"

export const useAuthStore = defineStore({
    id: "auth",
    state: () => ({
        // initialize state from local storage to enable user to stay logged in
        user: JSON.parse(localStorage.getItem("user") || "null"),
        returnUrl: null,
    }),
    actions: {
        async setup() {
            try {
                const { data: user } = await ToolShedApi().GET("/api/users/current")
                this.user = user
                // store user details and jwt in local storage to keep user logged in between page refreshes
                localStorage.setItem("user", user ? JSON.stringify(user) : "null")
            } catch (e) {
                console.debug(`Failed to get current user: ${errorMessageAsString(e)}`)
            }
        },
        async login(username: string, password: string) {
            const token = ensureCookie("session_csrf_token")
            ToolShedApi()
                .PUT("/api_internal/login", {
                    body: {
                        login: username,
                        password: password,
                        session_csrf_token: token,
                    },
                })
                .then(async () => {
                    // We need to do this outside the router to get updated
                    // cookies and hence csrf token.
                    window.location.href = "/login_success"
                })
                .catch(notifyOnCatch)
        },
        async logout() {
            const token = ensureCookie("session_csrf_token")
            ToolShedApi()
                .PUT("/api_internal/logout", {
                    body: {
                        session_csrf_token: token,
                        logout_all: false,
                    },
                })
                .then(async () => {
                    this.user = null
                    localStorage.removeItem("user")
                    // We need to do this outside the router to get updated
                    // cookies and hence csrf token.
                    window.location.href = "/logout_success"
                })
                .catch(notifyOnCatch)
        },
    },
})
