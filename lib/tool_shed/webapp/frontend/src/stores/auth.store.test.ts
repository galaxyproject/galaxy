import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { createPinia, setActivePinia } from "pinia"
import { useAuthStore } from "./auth.store"

vi.mock("@/schema", () => ({
    ToolShedApi: () => ({
        PUT: vi.fn().mockResolvedValue({}),
        GET: vi.fn().mockRejectedValue(new Error("Request failed with status 403")),
    }),
}))

describe("auth store login", () => {
    beforeEach(() => {
        setActivePinia(createPinia())
        document.cookie = "session_csrf_token=token"
        vi.stubGlobal("location", { href: "/login", origin: "http://localhost" })
    })

    afterEach(() => {
        vi.unstubAllGlobals()
    })

    it("lands on the page the user came to log in for", async () => {
        await useAuthStore().login("shuser", "secret", "/repos/devteam/bismark/shortlog")
        expect(window.location.href).toBe("/repos/devteam/bismark/shortlog")
    })

    it("falls back to the login success page without a return path, or with one off this site", async () => {
        await useAuthStore().login("shuser", "secret")
        expect(window.location.href).toBe("/login_success")
        await useAuthStore().login("shuser", "secret", "//evil.example")
        expect(window.location.href).toBe("/login_success")
    })
})

describe("auth store setup", () => {
    it("forgets a cached user whose session has expired", async () => {
        localStorage.setItem("user", JSON.stringify({ id: "1", username: "shuser" }))
        setActivePinia(createPinia())
        const store = useAuthStore()
        await store.setup()
        expect(store.user).toBeNull()
        expect(localStorage.getItem("user")).toBe("null")
    })
})
