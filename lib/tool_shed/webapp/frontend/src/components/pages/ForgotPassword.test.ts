import { describe, it, expect, beforeEach, vi } from "vitest"
import { mount, flushPromises } from "@vue/test-utils"
import ForgotPassword from "./ForgotPassword.vue"

const mockPost = vi.fn()
vi.mock("@/schema", () => ({
    ToolShedApi: () => ({
        POST: mockPost,
    }),
}))

describe("ForgotPassword", () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    it("submits the typed email and shows the sent confirmation", async () => {
        mockPost.mockResolvedValue({})

        const wrapper = mount(ForgotPassword, {
            global: { renderStubDefaultSlot: true, stubs: { QPage: true } },
        })

        await wrapper.find("input[name='email']").setValue("a@b.com")
        await wrapper.find("form[name='forgot_password']").trigger("submit")
        await flushPromises()

        expect(mockPost).toHaveBeenCalledWith(
            "/api_internal/reset_password",
            expect.objectContaining({ body: { email: "a@b.com", bear_field: "" } }),
        )
        expect(wrapper.find(".reset-password-sent").exists()).toBe(true)
    })

    it("shows an error banner when the request fails", async () => {
        mockPost.mockRejectedValue(new Error("no such account"))

        const wrapper = mount(ForgotPassword, {
            global: { renderStubDefaultSlot: true, stubs: { QPage: true } },
        })
        await wrapper.find("form[name='forgot_password']").trigger("submit")
        await flushPromises()

        expect(wrapper.find('[role="alert"]').text()).toContain("no such account")
    })
})
