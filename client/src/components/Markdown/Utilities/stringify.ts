export function stringify<T extends Record<string, any>>(contentObject: T): string {
    function deepSortObject(obj: any): any {
        if (typeof obj !== "object" || obj === null || Array.isArray(obj)) {
            return obj;
        }
        return Object.keys(obj)
            .sort()
            .reduce((acc, key) => {
                acc[key] = deepSortObject(obj[key]);
                return acc;
            }, {} as Record<string, any>);
    }
    const sortedObject = deepSortObject(contentObject);
    return JSON.stringify(sortedObject, null, 4);
}
