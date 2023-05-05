export type Message<O extends object, K extends keyof O> =
    | {
          type: "setArray";
          array: O[];
      }
    | {
          type: "setFilter";
          filter: string;
      }
    | {
          type: "setFields";
          fields: K[];
      };

export type ResultMessage<O extends object> = {
    type: "result";
    filtered: O[];
};

let array: Record<string, unknown>[] = [];
let filter = "";
let fields: string[] = [];

self.addEventListener("message", (e: MessageEvent<Message<Record<string, unknown>, string>>) => {
    const message = e.data;

    if (message.type === "setArray") {
        array = message.array;
    } else if (message.type === "setFields") {
        fields = message.fields;
    } else if (message.type === "setFilter") {
        filter = message.filter;
    }

    if (array.length > 0 && fields.length > 0) {
        const filtered = runFilter(filter, array, fields);
        self.postMessage({ type: "result", filtered });
    }
});

function runFilter(f: string, arr: Record<string, unknown>[], fields: string[]) {
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
