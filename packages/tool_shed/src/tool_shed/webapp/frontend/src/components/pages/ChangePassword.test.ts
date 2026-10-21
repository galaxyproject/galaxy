import { describe, it, expect, beforeEach, vi } from "vitest"
import { mount, flushPromises } from "@vue/test-utils"
import ChangePassword from "./ChangePassword.vue"

const mockPut = vi.fn()
vi.mock("@/schema", () => ({
    ToolShedApi: () => ({
        PUT: mockPut,
    }),
}))

const { mockPush } = vi.hoisted(() => ({ mockPush: vi.fn() }))
vi.mock("@/router", () => ({
    default: { push: mockPush },
}))

describe("ChangePassword", () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    it("submits the typed current, new and confirm passwords", async () => {
        mockPut.mockResolvedValue({})

        const wrapper = mount(ChangePassword)

        await wrapper.find("input[name='current']").setValue("oldpass")
        await wrapper.find("input[name='password']").setValue("newpass")
        await wrapper.find("input[name='confirm']").setValue("newpass")
        await wrapper.find("form").trigger("submit")
        await flushPromises()

        expect(mockPut).toHaveBeenCalledWith(
            "/api_internal/change_password",
            expect.objectContaining({
                body: { current: "oldpass", password: "newpass", confirm: "newpass" },
            }),
        )
        expect(mockPush).toHaveBeenCalledWith("/user/change_password_success")
    })

    it("shows an error banner when the change fails", async () => {
        mockPut.mockRejectedValue(new Error("wrong password"))

        const wrapper = mount(ChangePassword)
        await wrapper.find("form").trigger("submit")
        await flushPromises()

        expect(wrapper.find('[role="alert"]').text()).toContain("wrong password")
    })
})
