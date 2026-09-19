export function runFilter<O extends object, K extends keyof O>(f: string, arr: O[], fields: (K | string[])[]) {
    if (f === "") {
        return arr;
    } else {
        return arr.filter((obj) => {
            const lowerCaseFilter = f.toLocaleLowerCase();
            for (const field of fields) {
                let val: unknown;

                if (typeof field === "string") {
                    val = obj[field];
                } else if (Array.isArray(field)) {
                    val = field.reduce((acc: unknown, curr: string) => {
                        if (acc && typeof acc === "object") {
                            return (acc as Record<string, unknown>)[curr];
                        }
                        return undefined;
                    }, obj);
                }

                if (typeof val === "string") {
                    if (val.toLowerCase().includes(lowerCaseFilter)) {
                        return true;
                    }
                } else if (Array.isArray(val)) {
                    return val.find((v) => {
                        return typeof v === "string" ? v.toLowerCase().includes(lowerCaseFilter) : false;
                    });
                }
            }

            return false;
        });
    }
}
