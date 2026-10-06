import { describe, it, expect, beforeEach, afterEach, vi } from "vitest"
import { mount, flushPromises } from "@vue/test-utils"
import RepositoriesBySearch from "./RepositoriesBySearch.vue"

const mockReplace = vi.fn()
vi.mock("vue-router", () => ({
    useRoute: () => ({ query: {} }),
    useRouter: () => ({ replace: mockReplace }),
}))

// Stub the grid: it's not what's under test here, and has its own tests.
vi.mock("@/components/PaginatedRepositoriesGrid.vue", () => ({
    default: {
        name: "PaginatedRepositoriesGrid",
        props: ["title", "onRequest", "syncPageToUrl"],
        template: '<div class="stub-grid" />',
    },
}))

describe("RepositoriesBySearch", () => {
    beforeEach(() => {
        vi.useFakeTimers()
        vi.clearAllMocks()
    })

    afterEach(() => {
        vi.useRealTimers()
    })

    it("debounces typing before updating the route and showing results", async () => {
        const wrapper = mount(RepositoriesBySearch)

        const input = wrapper.find("input")
        await input.setValue("b")
        await input.setValue("bo")

        // debounce hasn't elapsed yet -- no route update, no grid
        expect(mockReplace).not.toHaveBeenCalled()
        expect(wrapper.find(".stub-grid").exists()).toBe(false)

        await vi.advanceTimersByTimeAsync(1000)
        await flushPromises()

        expect(mockReplace).toHaveBeenCalledWith({ query: { q: "bo" } })
        expect(wrapper.find(".stub-grid").exists()).toBe(true)
    })

    it("does not show the grid for a single-character query", async () => {
        const wrapper = mount(RepositoriesBySearch)

        await wrapper.find("input").setValue("b")
        await vi.advanceTimersByTimeAsync(1000)
        await flushPromises()

        expect(wrapper.find(".stub-grid").exists()).toBe(false)
    })
})
