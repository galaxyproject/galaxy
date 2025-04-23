import { type Plugin } from "@/api/plugins";

export function getTestUrls(plugin?: Plugin) {
    return (
        plugin?.tests?.flatMap((item) => {
            const url = item.param?.name === "dataset_id" ? item.param?.value : "";
            const name = getFilename(url).trim();
            const extension = getExtension(name);
            if (url && name && extension) {
                return [{ name, extension, url }];
            } else {
                return [];
            }
        }) ?? []
    );
}

function getFilename(url: string): string {
    try {
        const { pathname } = new URL(url);
        return pathname.split("/").filter(Boolean).pop() ?? "";
    } catch {
        return "";
    }
}

function getExtension(filename: string): string {
    const dot = filename.lastIndexOf(".");
    return dot >= 0 ? filename.slice(dot + 1).toLowerCase() : "";
}
