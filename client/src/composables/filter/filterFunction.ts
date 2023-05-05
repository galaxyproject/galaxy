export function runFilter<O extends object, K extends keyof O>(f: string, arr: O[], fields: K[]) {
    if (f === "") {
        return arr;
    } else {
        return arr.filter((obj) => {
            for (const field of fields) {
                const val = obj[field];

                if (typeof val === "string") {
                    if (val.toLowerCase().includes(f.toLocaleLowerCase())) {
                        return true;
                    }
                } else if (Array.isArray(val)) {
                    if (val.includes(f)) {
                        return true;
                    }
                }
            }

            return false;
        });
    }
}
