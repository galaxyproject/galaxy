import { describe, it, expect, beforeEach, vi } from "vitest"
import { mount, flushPromises } from "@vue/test-utils"
import RegisterPage from "./RegisterPage.vue"

const mockPost = vi.fn()
vi.mock("@/schema", () => ({
    ToolShedApi: () => ({
        POST: mockPost,
    }),
}))

const { mockPush } = vi.hoisted(() => ({ mockPush: vi.fn() }))
vi.mock("@/router", () => ({
    default: { push: mockPush },
}))

describe("RegisterPage", () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    it("submits the typed email, password, confirm and username", async () => {
        mockPost.mockResolvedValue({ data: { activation_error: false, activation_sent: true, email: "a@b.com" } })

        const wrapper = mount(RegisterPage)

        await wrapper.find("input[name='email']").setValue("a@b.com")
        await wrapper.find("input[name='password']").setValue("secretpass")
        await wrapper.find("input[name='confirm']").setValue("secretpass")
        await wrapper.find("input[name='username']").setValue("newuser")
        await wrapper.find("form[name='registration']").trigger("submit")
        await flushPromises()

        expect(mockPost).toHaveBeenCalledWith(
            "/api_internal/register",
            expect.objectContaining({
                body: {
                    email: "a@b.com",
                    password: "secretpass",
                    username: "newuser",
                    bear_field: "",
                },
            }),
        )
        expect(mockPush).toHaveBeenCalled()
    })
})
