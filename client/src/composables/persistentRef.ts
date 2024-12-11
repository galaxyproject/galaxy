/*
   vueuse local storage has some strange, buggy side-effects,
   so were re-implementing just the parts we need here
*/

import { type Ref, ref, watch } from "vue";

import { match } from "@/utils/utils";

function stringify(value: unknown): string {
    if (typeof value !== "object") {
        return `${value}`;
    } else {
        return JSON.stringify(value);
    }
}

function parse<T>(value: string, type: "string" | "number" | "boolean" | "object"): T {
    return match(type, {
        string: () => value as T,
        number: () => parseFloat(value) as T,
        boolean: () => (value.toLowerCase().trim() === "true" ? true : false) as T,
        object: () => JSON.parse(value),
    });
}

export function usePersistentRef(key: string, defaultValue: string): Ref<string>;
export function usePersistentRef(key: string, defaultValue: number): Ref<number>;
export function usePersistentRef<T>(key: string, defaultValue: T): Ref<T>;
export function usePersistentRef<T extends string | number | boolean | object | null>(
    key: string,
    defaultValue: T
): Ref<T> {
    const storageSyncedRef = ref(defaultValue) as Ref<T>;

    const stored = window.localStorage.getItem(key);

    if (stored) {
        try {
            storageSyncedRef.value = parse(stored, typeof defaultValue as "string" | "number" | "boolean" | "object");
        } catch (e) {
            console.error(`Failed to parse value "${stored}" from local storage key "${key}". Resetting key`);
            window.localStorage.removeItem(key);
        }
    } else {
        const stringified = stringify(storageSyncedRef.value);
        window.localStorage.setItem(key, stringified);
    }

    watch(
        () => storageSyncedRef.value,
        () => {
            const stringified = stringify(storageSyncedRef.value);
            window.localStorage.setItem(key, stringified);
        },
        { deep: true }
    );

    return storageSyncedRef;
}
