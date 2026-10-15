import { describe, expect, it } from "vitest"
import { buildFileTree, type FileTreeNode } from "./fileTree"

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
})
