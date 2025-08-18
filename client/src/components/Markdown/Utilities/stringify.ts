export function stringify<T extends Record<string, unknown>>(contentObject: T): string {
    function deepSortObject(obj: unknown): unknown {
        if (typeof obj !== "object" || obj === null || Array.isArray(obj)) {
            return obj;
        }
        return Object.keys(obj)
            .sort()
            .reduce((acc, key) => {
                acc[key] = deepSortObject((obj as Record<string, unknown>)[key]);
                return acc;
            }, {} as Record<string, unknown>);
    }
    const sortedObject = deepSortObject(contentObject);
    return JSON.stringify(sortedObject, null, 4);
}
