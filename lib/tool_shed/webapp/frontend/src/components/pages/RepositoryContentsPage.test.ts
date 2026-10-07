import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils"
import { defineComponent, h, ref } from "vue"
import RepositoryContentsPage from "./RepositoryContentsPage.vue"

const { mockFiles, mockContents, mockPush, mockReplace } = vi.hoisted(() => ({
    mockFiles: vi.fn(),
    mockContents: vi.fn(),
    mockPush: vi.fn(),
    mockReplace: vi.fn(),
}))

vi.mock("@/api", async (importOriginal) => ({
    ...(await importOriginal<typeof import("@/api")>()),
    repositoryFiles: mockFiles,
    repositoryFileContents: mockContents,
}))

vi.mock("vue-router", async (importOriginal) => ({
    ...(await importOriginal<typeof import("vue-router")>()),
    useRouter: () => ({ push: mockPush, replace: mockReplace }),
}))

type StoreRepository = { name: string; owner: string; deprecated?: boolean; deleted?: boolean }

const store = {
    loading: ref(false),
    repository: ref<StoreRepository | null>({ name: "column_maker", owner: "devteam" }),
    repositoryMetadata: ref<Record<string, unknown> | null>(null),
    setId: vi.fn(),
}

vi.mock("@/stores", () => ({
    useRepositoryStore: () => store,
}))

// Quasar's select isn't the subject here: expose the offered revisions and let tests pick one
const RevisionSelectStub = defineComponent({
    props: { revisions: { type: Object, required: true }, modelValue: { type: String, required: true } },
    emits: ["update:modelValue"],
    setup(props, { emit }) {
        return () =>
            h("div", { class: "revision-select-stub", "data-selected": props.modelValue }, [
                ...Object.values(props.revisions as Record<string, { changeset_revision: string }>).map((revision) =>
                    h(
                        "button",
                        {
                            class: "pick-revision",
                            onClick: () => emit("update:modelValue", revision.changeset_revision),
                        },
                        revision.changeset_revision,
                    ),
                ),
            ])
    },
})

function revision(changeset: string, overrides: Record<string, unknown> = {}) {
    return { changeset_revision: changeset, downloadable: true, malicious: false, ...overrides }
}

const files = [
    { path: "column_maker/column_maker.xml", size: 25, type: "file", executable: false },
    { path: "README.md", size: 6, type: "file", executable: false },
]

function contents(path: string, content = "<tool>") {
    return { path, size: content.length, type: "file", binary: false, truncated: false, content }
}

async function mountPage(props: Record<string, unknown> = {}) {
    const wrapper = mount(RepositoryContentsPage, {
        props: { repositoryId: "abc", ...props },
        global: {
            stubs: { RouterLink: { template: "<a><slot /></a>" }, RevisionSelect: RevisionSelectStub },
        },
    })
    await flushPromises()
    return wrapper
}

function offeredRevisions(wrapper: Awaited<ReturnType<typeof mountPage>>) {
    return wrapper.findAll(".pick-revision").map((button) => button.text())
}

// Pages share the mocked store, so a page left mounted would refetch when a later test resets it
enableAutoUnmount(afterEach)

describe("RepositoryContentsPage", () => {
    beforeEach(() => {
        vi.clearAllMocks()
        store.loading.value = false
        store.repository.value = { name: "column_maker", owner: "devteam" }
        store.repositoryMetadata.value = {
            "0:aaaaaaaaaaaa": revision("aaaaaaaaaaaa"),
            "1:bbbbbbbbbbbb": revision("bbbbbbbbbbbb"),
            "2:cccccccccccc": revision("cccccccccccc", { downloadable: false }),
            "3:dddddddddddd": revision("dddddddddddd", { malicious: true }),
        }
        mockFiles.mockImplementation(async (_id: string, changeset: string) => ({
            changeset_revision: changeset,
            files,
        }))
        mockContents.mockImplementation(async (_id: string, _changeset: string, path: string) => contents(path))
    })

    it("loads the repository and has one h1", async () => {
        const wrapper = await mountPage()

        expect(store.setId).toHaveBeenCalledWith("abc")
        const headings = wrapper.findAll("h1")
        expect(headings).toHaveLength(1)
        expect(headings[0].text()).toBe("Contents")
        expect(wrapper.text()).toContain("devteam")
    })

    it("offers only installable revisions and defaults to the newest", async () => {
        const wrapper = await mountPage()

        expect(offeredRevisions(wrapper)).toEqual(["aaaaaaaaaaaa", "bbbbbbbbbbbb"])
        expect(wrapper.get(".revision-select-stub").attributes("data-selected")).toBe("bbbbbbbbbbbb")
        expect(mockFiles).toHaveBeenCalledWith("abc", "bbbbbbbbbbbb")
        expect(wrapper.findAll(".repository-file-tree button").map((b) => b.text())).toEqual([
            "column_maker",
            "README.md",
        ])
        expect(wrapper.text()).toContain("Select a file to view its contents.")
        expect(mockContents).not.toHaveBeenCalled()
    })

    it("puts the file tree in a Files navigation landmark", async () => {
        const wrapper = await mountPage()

        expect(wrapper.get('nav[aria-label="Files"]').find(".repository-file-tree").exists()).toBe(true)
    })

    it("shows the revision and file from the URL", async () => {
        const wrapper = await mountPage({ revision: "aaaaaaaaaaaa", file: "column_maker/column_maker.xml" })

        expect(mockFiles).toHaveBeenCalledWith("abc", "aaaaaaaaaaaa")
        expect(mockContents).toHaveBeenCalledWith("abc", "aaaaaaaaaaaa", "column_maker/column_maker.xml")
        expect(wrapper.get("pre").text()).toBe("<tool>")
        expect(wrapper.get("[aria-current=true]").text()).toBe("column_maker.xml")
    })

    it("pushes a picked file onto the history so Back returns to the previous one", async () => {
        const wrapper = await mountPage()

        const readme = wrapper.findAll(".repository-file-tree button").find((b) => b.text() === "README.md")
        await readme?.trigger("click")

        expect(mockPush).toHaveBeenCalledWith("/repositories/abc/contents?file=README.md")
        expect(mockReplace).not.toHaveBeenCalled()
    })

    it("shows the file loading, not an empty viewer, while the listing for a linked file loads", async () => {
        mockFiles.mockImplementationOnce(() => new Promise(() => undefined))
        const wrapper = await mountPage({ revision: "aaaaaaaaaaaa", file: "README.md" })

        expect(wrapper.get(".contents-file-path").text()).toBe("README.md")
        expect(wrapper.get(".repository-file-viewer").text()).toContain("Loading file")
        expect(wrapper.text()).not.toContain("Select a file to view its contents.")
    })

    it("keeps the slashes of a nested file readable in the URL", async () => {
        const wrapper = await mountPage({ revision: "aaaaaaaaaaaa" })
        const treeButton = (name: string) =>
            wrapper.findAll(".repository-file-tree button").find((b) => b.text() === name)

        await treeButton("column_maker")?.trigger("click")
        await treeButton("column_maker.xml")?.trigger("click")

        expect(mockPush).toHaveBeenCalledWith(
            "/repositories/abc/contents?revision=aaaaaaaaaaaa&file=column_maker/column_maker.xml",
        )
    })

    it("puts a picked revision in the URL, keeping the file", async () => {
        const wrapper = await mountPage({ file: "README.md" })

        await wrapper.findAll(".pick-revision")[0].trigger("click")

        expect(mockReplace).toHaveBeenCalledWith("/repositories/abc/contents?revision=aaaaaaaaaaaa&file=README.md")
    })

    it("follows the URL to another file", async () => {
        const wrapper = await mountPage({ file: "README.md" })
        mockContents.mockResolvedValueOnce(contents("column_maker/column_maker.xml", '<tool id="x">'))

        await wrapper.setProps({ file: "column_maker/column_maker.xml" })
        await flushPromises()

        expect(wrapper.get("pre").text()).toBe('<tool id="x">')
    })

    it("says when the file is not in the selected revision", async () => {
        const wrapper = await mountPage({ file: "column_maker/test-data/gone.tsv" })

        expect(wrapper.text()).toContain("column_maker/test-data/gone.tsv is not in this revision.")
        expect(mockContents).not.toHaveBeenCalled()
    })

    it("says when the revision from the URL can't be browsed", async () => {
        const wrapper = await mountPage({ revision: "cccccccccccc" })

        expect(wrapper.text()).toContain("Revision cccccccccccc is not an installable revision of this repository.")
        expect(mockFiles).not.toHaveBeenCalled()
    })

    it.each(["deprecated", "deleted"])("says a %s repository's files can't be browsed", async (flag) => {
        store.repository.value = { name: "column_maker", owner: "devteam", [flag]: true }
        const wrapper = await mountPage({ file: "README.md" })

        expect(wrapper.text()).toContain(`This repository has been ${flag}, so its files can't be browsed.`)
        expect(wrapper.find(".repository-file-viewer").exists()).toBe(false)
        expect(mockFiles).not.toHaveBeenCalled()
        expect(mockContents).not.toHaveBeenCalled()
    })

    it("says when no revision can be browsed", async () => {
        store.repositoryMetadata.value = { "0:cccccccccccc": revision("cccccccccccc", { downloadable: false }) }
        const wrapper = await mountPage()

        expect(wrapper.text()).toContain("This repository has no installable revisions to browse.")
        expect(mockFiles).not.toHaveBeenCalled()
    })

    it("shows an error when the file listing fails", async () => {
        mockFiles.mockRejectedValue(new Error("Request failed with status 500"))
        const wrapper = await mountPage()

        expect(wrapper.get("[role=alert]").text()).toContain("Failed to load the files in this revision.")
    })

    it("shows an error when the file fails to load", async () => {
        mockContents.mockRejectedValue(new Error("Request failed with status 404"))
        const wrapper = await mountPage({ file: "README.md" })

        expect(wrapper.get("[role=alert]").text()).toContain("Request failed with status 404")
    })

    it("ignores a listing that arrives after the revision changed", async () => {
        let resolveSlow: ((value: unknown) => void) | undefined
        mockFiles.mockImplementationOnce(() => new Promise((resolve) => (resolveSlow = resolve)))
        const wrapper = await mountPage({ revision: "aaaaaaaaaaaa" })

        await wrapper.setProps({ revision: "bbbbbbbbbbbb" })
        await flushPromises()
        resolveSlow?.({ changeset_revision: "aaaaaaaaaaaa", files: [files[1]] })
        await flushPromises()

        expect(wrapper.findAll(".repository-file-tree button").map((b) => b.text())).toEqual([
            "column_maker",
            "README.md",
        ])
    })
})
