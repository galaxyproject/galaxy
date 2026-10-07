/** Turn a flat, slash-separated file listing into a folder tree. */

export interface FileTreeFile<T> {
    kind: "file"
    name: string
    path: string
    entry: T
}

export interface FileTreeFolder<T> {
    kind: "folder"
    name: string
    path: string
    children: FileTreeNode<T>[]
}

export type FileTreeNode<T> = FileTreeFile<T> | FileTreeFolder<T>

export function basename(path: string): string {
    return path.slice(path.lastIndexOf("/") + 1)
}

export function ancestorsOf(path: string): string[] {
    const segments = path.split("/").slice(0, -1)
    return segments.map((_, index) => segments.slice(0, index + 1).join("/"))
}

function sortNodes<T>(nodes: FileTreeNode<T>[]): FileTreeNode<T>[] {
    nodes.sort((a, b) => {
        if (a.kind !== b.kind) {
            return a.kind === "folder" ? -1 : 1
        }
        return a.name < b.name ? -1 : a.name > b.name ? 1 : 0
    })
    for (const node of nodes) {
        if (node.kind === "folder") {
            sortNodes(node.children)
        }
    }
    return nodes
}

export function buildFileTree<T extends { path: string }>(files: T[]): FileTreeNode<T>[] {
    const root: FileTreeNode<T>[] = []
    const folders = new Map<string, FileTreeFolder<T>>()
    for (const entry of files) {
        let siblings = root
        for (const folderPath of ancestorsOf(entry.path)) {
            let folder = folders.get(folderPath)
            if (!folder) {
                folder = { kind: "folder", name: basename(folderPath), path: folderPath, children: [] }
                folders.set(folderPath, folder)
                siblings.push(folder)
            }
            siblings = folder.children
        }
        siblings.push({ kind: "file", name: basename(entry.path), path: entry.path, entry })
    }
    return sortNodes(root)
}
