<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { computed } from "vue";

import { getAppRoot } from "@/onload";

const props = defineProps<{
    messages: string[];
}>();

const emit = defineEmits<{
    (e: "dismissed", index: number): void;
}>();

const loginLink = computed(() => `${getAppRoot()}login?redirect=${encodeURIComponent(window.location.toString())}`);

function hasLogin(string: string) {
    return string.includes("logged in");
}

function splitLoginString(string: string) {
    return string.split(/(logged in)/g);
}
</script>

<template>
    <div>
        <BAlert
            v-for="(message, index) in props.messages"
            :key="message"
            show
            variant="danger"
            dismissible
            @dismissed="() => emit('dismissed', index)">
            <span v-if="hasLogin(message)">
                <span v-for="(part, i) in splitLoginString(message)" :key="i">
                    <a v-if="hasLogin(part)" :href="loginLink" class="require-login-link">
                        {{ part }}
                    </a>
                    <span v-else> {{ part }} </span>
                </span>
            </span>
            <span v-else> {{ message }} </span>
        </BAlert>
    </div>
</template>
