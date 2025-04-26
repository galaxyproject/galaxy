import { type Plugin } from "@/api/plugins";

export function getTestExtensions(plugin?: Plugin): string[] {
    const results: string[] = [];
    if (plugin?.data_sources) {
        for (const dataSource of plugin.data_sources) {
            for (const test of dataSource.tests) {
                if (test.attr === "ext" && test.type === "eq" && test.result) {
                    results.push(test.result);
                }
            }
        }
    }
    return results;
}

export function getTestUrls(plugin?: Plugin) {
    return (
        plugin?.tests?.flatMap((item) => {
            const url = item.param?.name === "dataset_id" ? item.param?.value : "";
            const name = item.param?.label ?? getFilename(url);
            if (url && name) {
                return [{ name, url }];
            } else {
                return [];
            }
        }) ?? []
    );
}

export function getFilename(url: string): string {
    try {
        const { pathname } = new URL(url);
        const name = pathname.split("/").filter(Boolean).pop() ?? "";
        return name.trim();
    } catch {
        return "";
    }
}
