import { defineStore } from "pinia"
import { ensureCookie, notifyOnCatch } from "@/util"
import { getCurrentUser } from "@/apiUtil"

import { fetcher } from "@/schema"

const loginFetcher = fetcher.path("/api_internal/login").method("put").create()
const logoutFetcher = fetcher.path("/api_internal/logout").method("put").create()

export const useAuthStore = defineStore({
    id: "auth",
    state: () => ({
        // initialize state from local storage to enable user to stay logged in
        user: JSON.parse(localStorage.getItem("user") || "null"),
        returnUrl: null,
    }),
    actions: {
        async setup() {
            const user = await getCurrentUser()
            this.user = user
            // store user details and jwt in local storage to keep user logged in between page refreshes
            localStorage.setItem("user", user ? JSON.stringify(user) : "null")
        },
        async login(username: string, password: string) {
            const token = ensureCookie("session_csrf_token")
            console.log(token)
            loginFetcher({
                login: username,
                password: password,
                session_csrf_token: token,
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
            logoutFetcher({
                session_csrf_token: token,
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
