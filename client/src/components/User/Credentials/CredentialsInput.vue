<script setup lang="ts">
import { BBadge, BCard } from "bootstrap-vue";

import type { UserCredentials } from "@/api/users";

interface Props {
    credential: UserCredentials;
}

defineProps<Props>();
</script>

<template>
    <BCard>
        <h3>
            {{ credential.label || credential.name }}
            <BBadge
                v-if="credential.optional"
                variant="secondary"
                class="optional-credentials"
                title="These credentials are optional. If you do not provide them, the tool will use default values or
                    anonymous access.">
                Optional
            </BBadge>
            <BBadge
                v-else
                variant="danger"
                class="required-credentials"
                title="These credentials are required. You must provide them to use the tool.">
                Required
            </BBadge>
        </h3>
        <p>{{ credential.description }}</p>
        <div v-for="variable in credential.variables" :key="variable.name">
            <label :for="variable.name">{{ variable.label || variable.name }}</label>
            <input :id="variable.name" v-model="variable.value" type="text" autocomplete="off" />
        </div>
        <div v-for="secret in credential.secrets" :key="secret.name" class="secret-input">
            <label :for="secret.name">{{ secret.label || secret.name }}</label>
            <input :id="secret.name" v-model="secret.value" type="password" autocomplete="off" />
            <span v-if="secret.alreadySet" class="tick-icon">✔️</span>
        </div>
    </BCard>
</template>

<style scoped>
.secret-input {
    display: flex;
    align-items: center;
}
.tick-icon {
    color: green;
    margin-left: 0.5em;
}
</style>
