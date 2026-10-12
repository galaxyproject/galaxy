import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils"

import ResetPassword from "./ResetPassword.vue"

const { mockPut, mockPush, mockReplace } = vi.hoisted(() => ({
    mockPut: vi.fn(),
    mockPush: vi.fn(),
    mockReplace: vi.fn(),
}))
vi.mock("@/schema", () => ({
    ToolShedApi: () => ({
        PUT: mockPut,
    }),
}))

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

enableAutoUnmount(afterEach)

describe("ResetPassword", () => {
    beforeEach(() => {
        vi.resetAllMocks()
    })

    it("submits both password fields with the route token and opens the success page", async () => {
        mockPut.mockResolvedValue({})

        const wrapper = mount(ResetPassword)

        await wrapper.get("input[name='password']").setValue("newpass")
        await wrapper.get("input[name='confirm']").setValue("newpass")
        await wrapper.get("form[name='reset_password']").trigger("submit")
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
        await wrapper.get("form[name='reset_password']").trigger("submit")
        await flushPromises()

        expect(wrapper.get('[role="alert"]').text()).toContain("link expired")
    })
})
