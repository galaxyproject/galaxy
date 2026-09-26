import { defineStore } from "pinia";

import { useScopePointerStore } from "./scopePointerStore";

export function defineScopedStore<ID extends string, S>(id: ID, setup: (scopeId: string) => S) {
    return (scopeId: string) => {
        const { scope } = useScopePointerStore();

        return defineStore<`${ID}-${typeof scopeId}`, S>(`${id}-${scope(scopeId)}`, () => setup(scopeId))();
    };
}
