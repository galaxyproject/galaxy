import { mount } from "@vue/test-utils"
import { describe, expect, it } from "vitest"
import RepositoryFileTree from "./RepositoryFileTree.vue"

function entry(path: string, type: "file" | "symlink" = "file") {
    return { path, size: 10, type, executable: false }
}

const files = [
    entry("column_maker/column_maker.xml"),
    entry("column_maker/test-data/input.tsv"),
    entry("column_maker/link.xml", "symlink"),
    entry("README.md"),
]

function mountTree(selected: string | null = null) {
    return mount(RepositoryFileTree, { props: { files, selected } })
}

function button(wrapper: ReturnType<typeof mountTree>, name: string) {
    const match = wrapper.findAll("button").find((b) => b.text() === name)
    if (!match) {
        throw new Error(`no "${name}" button`)
    }
    return match
}

function visibleNames(wrapper: ReturnType<typeof mountTree>) {
    return wrapper.findAll("button").map((b) => b.text())
}

describe("RepositoryFileTree", () => {
    it("starts with folders collapsed, folders before files", () => {
        const wrapper = mountTree()

        expect(visibleNames(wrapper)).toEqual(["column_maker", "README.md"])
        expect(button(wrapper, "column_maker").attributes("aria-expanded")).toBe("false")
        expect(button(wrapper, "README.md").attributes("aria-expanded")).toBeUndefined()
    })

    it("expands and collapses a folder when it is clicked", async () => {
        const wrapper = mountTree()

        await button(wrapper, "column_maker").trigger("click")
        expect(button(wrapper, "column_maker").attributes("aria-expanded")).toBe("true")
        expect(visibleNames(wrapper)).toEqual([
            "column_maker",
            "test-data",
            "column_maker.xml",
            "link.xml",
            "README.md",
        ])

        await button(wrapper, "column_maker").trigger("click")
        expect(visibleNames(wrapper)).toEqual(["column_maker", "README.md"])
    })

    it("asks to select a file when it is clicked", async () => {
        const wrapper = mountTree()

        await button(wrapper, "README.md").trigger("click")

        expect(wrapper.emitted("select")).toEqual([["README.md"]])
    })

    it("opens the folders around the selected file and marks it current", () => {
        const wrapper = mountTree("column_maker/test-data/input.tsv")

        expect(button(wrapper, "column_maker").attributes("aria-expanded")).toBe("true")
        expect(button(wrapper, "test-data").attributes("aria-expanded")).toBe("true")
        expect(button(wrapper, "input.tsv").attributes("aria-current")).toBe("true")
        expect(wrapper.findAll("[aria-current]")).toHaveLength(1)
    })

    it("opens the folders around a file selected later", async () => {
        const wrapper = mountTree()

        await wrapper.setProps({ selected: "column_maker/column_maker.xml" })

        expect(button(wrapper, "column_maker").attributes("aria-expanded")).toBe("true")
        expect(button(wrapper, "column_maker.xml").attributes("aria-current")).toBe("true")
    })
})
