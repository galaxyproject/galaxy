import { beforeEach, describe, expect, it, vi } from "vitest"
import { flushPromises, mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { useRepositoryStore } from "@/stores"
import RepositoryExplore from "@/components/RepositoryExplore.vue"
import RepositoryPage from "./RepositoryPage.vue"

const { readmes, mockGet } = vi.hoisted(() => {
    const readmes = { value: {} as Record<string, string> }
    return { readmes, mockGet: vi.fn(async () => ({ data: readmes.value })) }
})
vi.mock("@/schema", async (importOriginal) => ({
    ...(await importOriginal<typeof import("@/schema")>()),
    ToolShedApi: () => ({ GET: mockGet }),
}))

function repository(overrides: Record<string, unknown> = {}) {
    return {
        id: "repo1",
        name: "concat",
        owner: "devteam",
        description: "Concatenate datasets",
        long_description: null,
        deprecated: false,
        update_time: "2024-01-01T00:00:00",
        times_downloaded: 3,
        ...overrides,
    }
}

function revision(overrides: Record<string, unknown> = {}) {
    return {
        "0:abc123": {
            changeset_revision: "abc123",
            create_time: "2024-01-01T00:00:00",
            downloadable: true,
            malicious: false,
            tools: [],
            invalid_tools: [],
            ...overrides,
        },
    }
}

// Metadata lands after mount, as it does from the store's fetch, so the page picks the newest revision
async function mountPage({ repositoryMetadata, ...state }: Record<string, unknown>) {
    const store = useRepositoryStore()
    vi.spyOn(store, "setId").mockResolvedValue(undefined)
    store.$patch({ loading: false, empty: false, repositoryPermissions: { can_manage: false }, ...state })
    const wrapper = mount(RepositoryPage, {
        props: { repositoryId: "repo1" },
        global: {
            stubs: {
                RouterLink: { template: "<a><slot /></a>" },
                RevisionSelect: true,
                RepositoryExplore: true,
                RepositoryActions: true,
                RevisionActions: true,
                ManagePushAccess: true,
                RepositoryLinks: true,
            },
        },
    })
    store.$patch({ repositoryMetadata } as Record<string, unknown>)
    await flushPromises()
    return wrapper
}

describe("RepositoryPage", () => {
    beforeEach(() => {
        setActivePinia(createPinia())
        readmes.value = {}
        mockGet.mockClear()
    })

    it("flags a deprecated repository and a malicious revision", async () => {
        const wrapper = await mountPage({
            repository: repository({ deprecated: true }),
            repositoryMetadata: revision({ malicious: true }),
        })

        expect(wrapper.text()).toContain("This repository has been deprecated.")
        expect(wrapper.text()).toContain("marked as malicious")
    })

    it("shows neither alert for a healthy repository", async () => {
        const wrapper = await mountPage({ repository: repository(), repositoryMetadata: revision() })

        expect(wrapper.text()).not.toContain("deprecated")
        expect(wrapper.text()).not.toContain("malicious")
    })

    it("loads the newest revision's READMEs and renders them as HTML", async () => {
        readmes.value = { "README.txt": "<p>hello&nbsp;readme</p>" }
        const wrapper = await mountPage({ repository: repository(), repositoryMetadata: revision() })

        expect(mockGet).toHaveBeenCalledWith(
            "/api/repositories/{encoded_repository_id}/revisions/{changeset_revision}/readmes",
            { params: { path: { encoded_repository_id: "repo1", changeset_revision: "abc123" } } },
        )
        const readme = wrapper.get(".repository-readme-wrapper")
        expect(readme.find("p").text()).toBe("hello\u00a0readme")
    })

    it("puts the description in the header and leaves out an About card with nothing more to say", async () => {
        const wrapper = await mountPage({
            repository: repository({ long_description: "Concatenate datasets" }),
            repositoryMetadata: revision(),
        })

        expect(wrapper.get(".page-header-subtitle").text()).toBe("Concatenate datasets")
        expect(wrapper.text()).not.toContain("About")
    })

    it("shows a long description that adds to the header's", async () => {
        const wrapper = await mountPage({
            repository: repository({ long_description: "Joins datasets head to tail, with options." }),
            repositoryMetadata: revision(),
        })

        expect(wrapper.get(".description").text()).toBe("Joins datasets head to tail, with options.")
    })

    it.each([
        ["a downloadable revision", {}, "abc123"],
        ["a revision that is not downloadable", { downloadable: false }, null],
        ["a malicious revision", { malicious: true }, null],
    ])(
        "points the explore menu's contents at %s only if the files API serves it",
        async (_label, overrides, expected) => {
            const wrapper = await mountPage({ repository: repository(), repositoryMetadata: revision(overrides) })

            expect(wrapper.findComponent(RepositoryExplore).props("browsableRevision")).toBe(expected)
        },
    )
})
