import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { createPinia, setActivePinia } from "pinia"
import { ApiRequestError } from "@/schema"
import { useAuthStore } from "./auth.store"

const getCurrentUser = vi.fn()

vi.mock("@/schema", async (importOriginal) => ({
    ...(await importOriginal<typeof import("@/schema")>()),
    ToolShedApi: () => ({
        PUT: vi.fn().mockResolvedValue({}),
        GET: getCurrentUser,
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
    const cachedUser = { id: "1", username: "shuser" }

    beforeEach(() => {
        localStorage.setItem("user", JSON.stringify(cachedUser))
        setActivePinia(createPinia())
    })

    it("forgets a cached user whose session has expired", async () => {
        getCurrentUser.mockRejectedValueOnce(new ApiRequestError(403))
        const store = useAuthStore()
        await store.setup()
        expect(store.user).toBeNull()
        expect(localStorage.getItem("user")).toBe("null")
    })

    it("keeps the cached user when the session check fails on the server", async () => {
        getCurrentUser.mockRejectedValueOnce(new ApiRequestError(502))
        const store = useAuthStore()
        await store.setup()
        expect(store.user).toEqual(cachedUser)
        expect(localStorage.getItem("user")).toBe(JSON.stringify(cachedUser))
    })
})
