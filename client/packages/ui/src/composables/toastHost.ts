import { computed, ref } from "vue";

const hosts = ref<string[]>([]);

export const activeToastHost = computed(() => hosts.value[hosts.value.length - 1]);

export function registerToastHost(host: string) {
    const index = hosts.value.indexOf(host);

    if (index !== -1) {
        hosts.value.splice(index, 1);
    }

    hosts.value.push(host);
}

export function unregisterToastHost(host: string) {
    const index = hosts.value.lastIndexOf(host);

    if (index !== -1) {
        hosts.value.splice(index, 1);
    }
}
