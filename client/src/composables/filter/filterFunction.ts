export function runFilter<O extends object, K extends keyof O>(f: string, arr: O[], fields: K[], asRegex = false) {
    let regex: RegExp | null = null;

    if (asRegex) {
        try {
            regex = new RegExp(f);
        } catch (e) {
            // ignore
        }
    }

    if (f === "") {
        return arr;
    } else {
        return arr.filter((obj) => {
            for (const field of fields) {
                const val = obj[field];

                if (typeof val === "string") {
                    if (regex) {
                        return val.match(regex);
                    } else if (val.toLowerCase().includes(f.toLocaleLowerCase())) {
                        return true;
                    }
                } else if (Array.isArray(val)) {
                    if (regex) {
                        return val.some((v) => {
                            if (typeof v === "string") {
                                return v.match(regex!);
                            } else {
                                return false;
                            }
                        });
                    } else if (val.includes(f)) {
                        return true;
                    }
                }
            }

            return false;
        });
    }
}
