import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { enableAutoUnmount, flushPromises, mount, type VueWrapper } from "@vue/test-utils"
import { createMemoryRouter } from "@/test-utils"
import ForgotPassword from "./ForgotPassword.vue"

const mockPost = vi.fn()
vi.mock("@/schema", () => ({
    ToolShedApi: () => ({
        POST: mockPost,
    }),
}))

const SELECTORS = {
    EMAIL_INPUT: "input[name='email']",
    FORM: "form[name='forgot_password']",
    SENT_CONFIRMATION: ".reset-password-sent",
    ERROR_BANNER: '[role="alert"]',
}

enableAutoUnmount(afterEach)

function mountForgotPassword() {
    return mount(ForgotPassword, { global: { plugins: [createMemoryRouter()] } })
}

async function submit(wrapper: VueWrapper) {
    await wrapper.find(SELECTORS.FORM).trigger("submit")
    await flushPromises()
}

describe("ForgotPassword", () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    it("links back to the login page", () => {
        const wrapper = mountForgotPassword()

        expect(wrapper.get("a[href='/login']").text()).toBe("Login.")
    })

    it("submits the typed email and shows the sent confirmation", async () => {
        mockPost.mockResolvedValue({})
        const wrapper = mountForgotPassword()

        await wrapper.find(SELECTORS.EMAIL_INPUT).setValue("a@b.com")
        await submit(wrapper)

        expect(mockPost).toHaveBeenCalledWith(
            "/api_internal/reset_password",
            expect.objectContaining({ body: { email: "a@b.com", bear_field: "" } }),
        )
        expect(wrapper.find(SELECTORS.SENT_CONFIRMATION).exists()).toBe(true)
        expect(wrapper.find(SELECTORS.FORM).exists()).toBe(false)
        expect(wrapper.find(SELECTORS.ERROR_BANNER).exists()).toBe(false)
    })

    it("shows an error banner and keeps the form when the request fails", async () => {
        mockPost.mockRejectedValue(new Error("no such account"))
        const wrapper = mountForgotPassword()

        await submit(wrapper)

        expect(wrapper.find(SELECTORS.ERROR_BANNER).text()).toContain("no such account")
        expect(wrapper.find(SELECTORS.FORM).exists()).toBe(true)
        expect(wrapper.find(SELECTORS.SENT_CONFIRMATION).exists()).toBe(false)
    })
})
