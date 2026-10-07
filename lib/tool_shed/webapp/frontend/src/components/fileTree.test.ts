import { describe, expect, it } from "vitest"
import { ancestorsOf, basename, buildFileTree, type FileTreeNode } from "./fileTree"

function names(nodes: FileTreeNode<{ path: string }>[]): unknown[] {
    return nodes.map((node) => (node.kind === "folder" ? { [node.name]: names(node.children) } : node.name))
}

describe("buildFileTree", () => {
    it("nests files under their folders, folders first then alphabetical", () => {
        const tree = buildFileTree([
            { path: "README.md" },
            { path: "tool/test-data/input.tsv" },
            { path: "tool/tool.xml" },
            { path: "tool/macros.xml" },
            { path: "LICENSE" },
            { path: "docs/index.md" },
        ])

        expect(names(tree)).toEqual([
            { docs: ["index.md"] },
            { tool: [{ "test-data": ["input.tsv"] }, "macros.xml", "tool.xml"] },
            "LICENSE",
            "README.md",
        ])
    })

    it("gives folders their full path and keeps each file's entry", () => {
        const entry = { path: "a/b/c.xml", size: 12 }
        const [folder] = buildFileTree([entry])

        expect(folder.kind).toBe("folder")
        expect(folder.path).toBe("a")
        const inner = folder.kind === "folder" ? folder.children[0] : null
        expect(inner?.path).toBe("a/b")
        const file = inner?.kind === "folder" ? inner.children[0] : null
        expect(file).toEqual({ kind: "file", name: "c.xml", path: "a/b/c.xml", entry })
    })

    it("returns no nodes for no files", () => {
        expect(buildFileTree([])).toEqual([])
    })
})

describe("ancestorsOf", () => {
    it("lists the folders containing a path, outermost first", () => {
        expect(ancestorsOf("a/b/c.xml")).toEqual(["a", "a/b"])
    })

    it("has no ancestors for a top-level file", () => {
        expect(ancestorsOf("README.md")).toEqual([])
    })
})

describe("basename", () => {
    it("returns the last path segment", () => {
        expect(basename("column_maker/column_maker.xml")).toBe("column_maker.xml")
        expect(basename("LICENSE")).toBe("LICENSE")
    })
})
