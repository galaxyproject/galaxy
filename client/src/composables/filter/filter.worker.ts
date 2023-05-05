import { runFilter } from "./filterFunction";

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
