import { useMagicKeys as wrappedUseMagicKeys } from "@vueuse/core";
import Vue from "vue";

export function useMagicKeys() {
    // a version of useMagicKeys from vueuse/core that doesn't console.error the
    // the message [Vue warn]: Vue 2 does not support reactive collection types such as Map or Set.
    // in all our tests. This can be dropped after the migration to Vue3.
    const oldSlientConfig = Vue.config.silent;
    try {
        Vue.config.silent = true;
        return wrappedUseMagicKeys();
    } finally {
        Vue.config.silent = oldSlientConfig;
    }
}
