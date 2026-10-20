import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { createPinia, setActivePinia } from "pinia"
import { useAuthStore } from "./auth.store"

vi.mock("@/schema", () => ({
    ToolShedApi: () => ({ PUT: vi.fn().mockResolvedValue({}) }),
}))

describe("auth store login", () => {
    beforeEach(() => {
        setActivePinia(createPinia())
        document.cookie = "session_csrf_token=token"
        vi.stubGlobal("location", { href: "/login" })
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
