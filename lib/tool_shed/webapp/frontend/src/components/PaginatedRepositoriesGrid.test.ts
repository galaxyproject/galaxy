import { describe, it, expect, vi } from "vitest"
import { mount, flushPromises } from "@vue/test-utils"
import PaginatedRepositoriesGrid from "./PaginatedRepositoriesGrid.vue"
import { emptyQueryResults } from "./RepositoriesGridInterface"

// RepositoryExplore (rendered inside q-table's row template) pulls in @/router,
// which calls createRouter() at import time -- keep the real exports around
// that and only override the composables this component actually calls.
vi.mock("vue-router", async (importOriginal) => {
    const actual = await importOriginal<typeof import("vue-router")>()
    return {
        ...actual,
        useRoute: () => ({ query: {} }),
        useRouter: () => ({ replace: vi.fn() }),
    }
})

describe("PaginatedRepositoriesGrid filter input", () => {
    it("renders the filter input when allowSearch is set, and updates as typed", async () => {
        const wrapper = mount(PaginatedRepositoriesGrid, {
            props: {
                allowSearch: true,
                onRequest: vi.fn().mockResolvedValue(emptyQueryResults()),
            },
        })
        await flushPromises()

        const filterInput = wrapper.find("input")
        expect(filterInput.exists()).toBe(true)

        await filterInput.setValue("bowtie")

        expect((filterInput.element as HTMLInputElement).value).toBe("bowtie")
    })

    it("does not render the filter input when allowSearch is unset", async () => {
        const wrapper = mount(PaginatedRepositoriesGrid, {
            props: {
                onRequest: vi.fn().mockResolvedValue(emptyQueryResults()),
            },
        })
        await flushPromises()

        expect(wrapper.find("input").exists()).toBe(false)
    })
})
