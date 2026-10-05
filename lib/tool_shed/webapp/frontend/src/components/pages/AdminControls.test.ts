import { describe, it, expect, beforeEach, vi } from "vitest"
import { mount, flushPromises } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { useUsersStore } from "@/stores"
import AdminControls from "./AdminControls.vue"

const mockPut = vi.fn()
vi.mock("@/schema", () => ({
    ToolShedApi: () => ({
        PUT: mockPut,
    }),
}))

vi.mock("@/components/SelectUser.vue", () => ({
    default: {
        name: "SelectUser",
        emits: ["selectedUser", "cleared"],
        template: "<div>stubbed select-user</div>",
    },
}))

describe("AdminControls", () => {
    beforeEach(() => {
        setActivePinia(createPinia())
        vi.clearAllMocks()
        useUsersStore().$patch({ users: [{ username: "shuser", id: "encoded123" }] as never })
    })

    it("resets the typed password for the selected user", async () => {
        mockPut.mockResolvedValue({})

        const wrapper = mount(AdminControls, {
            global: { renderStubDefaultSlot: true, stubs: { QPage: true } },
        })

        await wrapper.findComponent({ name: "SelectUser" }).vm.$emit("selectedUser", "shuser")
        await wrapper.find("input[name='password']").setValue("newpass")
        await wrapper.find("input[name='confirm']").setValue("newpass")
        await wrapper.find("form").trigger("submit")
        await flushPromises()

        expect(mockPut).toHaveBeenCalledWith(
            "/api/users/{encoded_user_id}/password",
            expect.objectContaining({
                params: { path: { encoded_user_id: "encoded123" } },
                body: { password: "newpass", confirm: "newpass" },
            }),
        )
    })
})
