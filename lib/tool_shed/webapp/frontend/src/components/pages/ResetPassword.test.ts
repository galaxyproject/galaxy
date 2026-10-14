import { describe, it, expect, beforeEach, vi } from "vitest"
import { mount, flushPromises } from "@vue/test-utils"
import ResetPassword from "./ResetPassword.vue"

const mockPut = vi.fn()
vi.mock("@/schema", () => ({
    ToolShedApi: () => ({
        PUT: mockPut,
    }),
}))

const { mockPush, mockReplace } = vi.hoisted(() => ({ mockPush: vi.fn(), mockReplace: vi.fn() }))
vi.mock("@/router", () => ({
    default: { push: mockPush, replace: mockReplace },
}))

vi.mock("vue-router", async () => {
    const actual = await vi.importActual<typeof import("vue-router")>("vue-router")
    return {
        ...actual,
        useRoute: () => ({ query: { token: "reset-token-abc" } }),
    }
})

describe("ResetPassword", () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    it("submits the typed password and confirm along with the route token", async () => {
        mockPut.mockResolvedValue({})

        const wrapper = mount(ResetPassword)

        await wrapper.find("input[name='password']").setValue("newpass")
        await wrapper.find("input[name='confirm']").setValue("newpass")
        await wrapper.find("form[name='reset_password']").trigger("submit")
        await flushPromises()

        expect(mockPut).toHaveBeenCalledWith(
            "/api_internal/change_password",
            expect.objectContaining({
                body: { token: "reset-token-abc", password: "newpass", confirm: "newpass" },
            }),
        )
        expect(mockPush).toHaveBeenCalledWith("/user/change_password_success")
    })

    it("shows an error banner when the request fails", async () => {
        mockPut.mockRejectedValue(new Error("link expired"))

        const wrapper = mount(ResetPassword)
        await wrapper.find("form[name='reset_password']").trigger("submit")
        await flushPromises()

        expect(wrapper.find('[role="alert"]').text()).toContain("link expired")
    })
})
