import { describe, it, expect, beforeEach, vi } from "vitest"
import { mount, flushPromises } from "@vue/test-utils"
import ManageApiKey from "./ManageApiKey.vue"

const mockGet = vi.fn()
const mockDelete = vi.fn()
const mockPost = vi.fn()
vi.mock("@/schema", () => ({
    ToolShedApi: () => ({
        GET: mockGet,
        DELETE: mockDelete,
        POST: mockPost,
    }),
}))

vi.mock("@/util", () => ({
    notify: vi.fn(),
    notifyOnCatch: vi.fn(),
    copyAndNotify: vi.fn(),
    errorMessageAsString: (e: unknown) => (e instanceof Error ? e.message : String(e)),
}))

describe("ManageApiKey", () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    it("displays the fetched API key in the readonly input", async () => {
        mockGet.mockResolvedValue({ data: "abc123key" })

        const wrapper = mount(ManageApiKey, {
            global: { renderStubDefaultSlot: true, stubs: { QPage: true } },
        })
        await flushPromises()

        const input = wrapper.find("input").element as HTMLInputElement
        expect(input.value).toBe("abc123key")
        expect(input.readOnly).toBe(true)
    })

    it("regenerates the key when the regenerate button is clicked", async () => {
        mockGet.mockResolvedValue({ data: "abc123key" })
        mockPost.mockResolvedValue({ data: "newkey456" })

        const wrapper = mount(ManageApiKey, {
            global: { renderStubDefaultSlot: true, stubs: { QPage: true } },
        })
        await flushPromises()

        await wrapper.find("button[aria-label='Regenerate API key']").trigger("click")
        await flushPromises()

        expect(mockPost).toHaveBeenCalledWith(
            "/api/users/{encoded_user_id}/api_key",
            expect.objectContaining({ params: { path: { encoded_user_id: "current" } } }),
        )
        expect((wrapper.find("input").element as HTMLInputElement).value).toBe("newkey456")
    })

    it("deactivates the key when the deactivate button is clicked", async () => {
        mockGet.mockResolvedValue({ data: "abc123key" })
        mockDelete.mockResolvedValue({})

        const wrapper = mount(ManageApiKey, {
            global: { renderStubDefaultSlot: true, stubs: { QPage: true } },
        })
        await flushPromises()

        await wrapper.find("button[aria-label='Deactivate API key']").trigger("click")
        await flushPromises()

        expect(mockDelete).toHaveBeenCalled()
        expect((wrapper.find("input").element as HTMLInputElement).value).toBe("")
    })
})
