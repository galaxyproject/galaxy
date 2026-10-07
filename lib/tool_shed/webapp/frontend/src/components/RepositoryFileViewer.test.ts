import { mount } from "@vue/test-utils"
import { describe, expect, it } from "vitest"
import type { RepositoryFileContents } from "@/api"
import RepositoryFileViewer from "./RepositoryFileViewer.vue"

function contents(overrides: Partial<RepositoryFileContents> = {}): RepositoryFileContents {
    return {
        path: "column_maker/column_maker.xml",
        size: 18,
        type: "file",
        binary: false,
        truncated: false,
        content: '<tool id="Add_a_column1">',
        ...overrides,
    }
}

function mountViewer(props: { file: RepositoryFileContents | null; loading?: boolean; error?: string }) {
    return mount(RepositoryFileViewer, { props })
}

describe("RepositoryFileViewer", () => {
    it("shows a text file with copy and download buttons", () => {
        const wrapper = mountViewer({ file: contents() })

        expect(wrapper.get("pre").text()).toBe('<tool id="Add_a_column1">')
        expect(wrapper.get(".config-file-contents-name").text()).toBe("column_maker.xml")
        expect(wrapper.find('[aria-label="Copy contents"]').exists()).toBe(true)
        expect(wrapper.find('[aria-label="Download"]').exists()).toBe(true)
    })

    it("explains a binary file instead of showing it", () => {
        const wrapper = mountViewer({ file: contents({ binary: true, content: null }) })

        expect(wrapper.find("pre").exists()).toBe(false)
        expect(wrapper.text()).toContain("column_maker.xml is a binary file and can't be shown here.")
    })

    it("explains a file too large to show, with its size", () => {
        const wrapper = mountViewer({ file: contents({ truncated: true, content: null, size: 3 * 1024 * 1024 }) })

        expect(wrapper.find("pre").exists()).toBe(false)
        expect(wrapper.text()).toContain("column_maker.xml is too large to show here (3.0 MB).")
    })

    it("explains a symbolic link", () => {
        const wrapper = mountViewer({ file: contents({ type: "symlink", content: null }) })

        expect(wrapper.find("pre").exists()).toBe(false)
        expect(wrapper.text()).toContain("column_maker.xml is a symbolic link, so it has no contents to show.")
    })

    it("says when a file is empty", () => {
        const wrapper = mountViewer({ file: contents({ content: "", size: 0 }) })

        expect(wrapper.find("pre").exists()).toBe(false)
        expect(wrapper.text()).toContain("column_maker.xml is empty.")
    })

    it("shows an error as an alert", () => {
        const wrapper = mountViewer({ file: null, error: "Request failed with status 404" })

        expect(wrapper.get('[role="alert"]').text()).toContain("Request failed with status 404")
        expect(wrapper.find("pre").exists()).toBe(false)
    })

    it("shows progress while the file loads", () => {
        const wrapper = mountViewer({ file: null, loading: true })

        expect(wrapper.find('[role="status"]').text()).toContain("Loading file")
    })

    it("prompts to pick a file when none is selected", () => {
        const wrapper = mountViewer({ file: null })

        expect(wrapper.text()).toContain("Select a file to view its contents.")
    })
})
