import { describe, it, expect, beforeEach, vi } from "vitest"
import { mount, flushPromises } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { useAuthStore } from "@/stores"
import LoginForm from "./LoginForm.vue"

// Typed values have to reach login() through GFormInput's modelValue binding
describe("LoginForm", () => {
    beforeEach(() => {
        setActivePinia(createPinia())
        vi.clearAllMocks()
    })

    it("submits the typed username and password", async () => {
        const loginSpy = vi.spyOn(useAuthStore(), "login").mockResolvedValue(undefined)

        const wrapper = mount(LoginForm)

        await wrapper.find("input[name='login']").setValue("shuser")
        await wrapper.find("input[name='password']").setValue("secret")
        await wrapper.find("form").trigger("submit")
        await flushPromises()

        expect(loginSpy).toHaveBeenCalledWith("shuser", "secret")
    })

    it("seeds the username from the initialLogin prop", () => {
        const wrapper = mount(LoginForm, { props: { initialLogin: "prefilled" } })

        expect((wrapper.find("input[name='login']").element as HTMLInputElement).value).toBe("prefilled")
    })

    it("shows an error banner when login fails", async () => {
        vi.spyOn(useAuthStore(), "login").mockRejectedValue(new Error("bad credentials"))

        const wrapper = mount(LoginForm)
        await wrapper.find("form").trigger("submit")
        await flushPromises()

        expect(wrapper.find('[role="alert"]').text()).toContain("bad credentials")
    })
})
