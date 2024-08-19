/*
   vueuse local storage has some strange, buggy side-effects,
   so were re-implementing just the parts we need here
*/

import { type Ref, ref, watch } from "vue";

import { match } from "@/utils/utils";

function serialize(value: unknown): string {
    if (typeof value !== "object") {
        return `${value}`;
    } else {
        return JSON.stringify(value);
    }
}

function deserialize<T>(value: string, type: "string" | "number" | "boolean" | "object"): T {
    return match(type, {
        string: () => value as T,
        number: () => parseFloat(value) as T,
        boolean: () => (value.toLocaleLowerCase().trim() === "true" ? true : false) as T,
        object: () => JSON.parse(value),
    });
}

export function useLocalStorage(key: string, defaultValue: string): Ref<string>;
export function useLocalStorage(key: string, defaultValue: boolean): Ref<boolean>;
export function useLocalStorage(key: string, defaultValue: number): Ref<number>;
export function useLocalStorage<T>(key: string, defaultValue: T): Ref<T>;
export function useLocalStorage<T extends string | number | boolean | object | null>(
    key: string,
    defaultValue: T
): Ref<T> {
    const storageSyncedRef = ref(defaultValue) as Ref<T>;

    const stored = localStorage.getItem(key);

    if (stored) {
        try {
            storageSyncedRef.value = deserialize(
                stored,
                typeof defaultValue as "string" | "number" | "boolean" | "object"
            );
        } catch (e) {
            console.error(`Failed to parse value "${stored}" from local storage key "${key}". Resetting key`);
            localStorage.removeItem(key);
        }
    } else {
        const stringified = serialize(storageSyncedRef.value);
        localStorage.setItem(key, stringified);
    }

    watch(
        () => storageSyncedRef.value,
        () => {
            const stringified = serialize(storageSyncedRef.value);
            localStorage.setItem(key, stringified);
        }
    );

    return storageSyncedRef;
}
