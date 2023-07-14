<template>
    <div v-if="hasMessages" class="mx-3 my-2">
        <GAlert :show="history.isDeleted" variant="warning">
            {{ "This history has been deleted" | localize }}
        </GAlert>
        <GAlert :show="userOverQuota" variant="warning">
            {{
                "You are over your disk quota. Tool execution is on hold until your disk usage drops below your allocated quota."
                    | localize
            }}
        </GAlert>
    </div>
</template>

<script>
import GAlert from "@/component-library/GAlert.vue";

export default {
    components: {
        GAlert,
    },
    props: {
        history: { type: Object, required: true },
    },
    data() {
        return {
            userOverQuota: false,
        };
    },
    computed: {
        hasMessages() {
            return this.userOverQuota || history.isDeleted;
        },
    },
};
</script>
