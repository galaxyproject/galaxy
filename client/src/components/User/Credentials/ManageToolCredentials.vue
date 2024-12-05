<script setup lang="ts">
import { ref } from "vue";

import type { UserCredentials } from "@/api/users";

import CredentialsInput from "@/components/User/Credentials/CredentialsInput.vue";

interface ManageToolCredentialsProps {
    toolId: string;
    toolVersion: string;
    credentials?: UserCredentials[];
}

const props = defineProps<ManageToolCredentialsProps>();

const providedCredentials = ref<UserCredentials[]>(initializeCredentials());

const emit = defineEmits<{
    (e: "save-credentials", credentials: UserCredentials[]): void;
}>();

function saveCredentials() {
    emit("save-credentials", providedCredentials.value);
}

function initializeCredentials(): UserCredentials[] {
    // If credentials are provided, clone them to avoid modifying the original data
    return props.credentials ? JSON.parse(JSON.stringify(props.credentials)) : [];
}
</script>

<template>
    <div>
        <p>
            Here you can manage your credentials for the tool <strong>{{ toolId }}</strong> version
            <strong> {{ toolVersion }} </strong>.
        </p>
        <CredentialsInput
            v-for="credential in providedCredentials"
            :key="credential.reference"
            :credential="credential" />
        <button @click="saveCredentials">Save Credentials</button>
    </div>
</template>

<style scoped>
.credential-card {
    border: 1px solid #ccc;
    padding: 1em;
    margin-bottom: 1em;
    border-radius: 5px;
}
.secret-input {
    display: flex;
    align-items: center;
}
.tick-icon {
    color: green;
    margin-left: 0.5em;
}
</style>
