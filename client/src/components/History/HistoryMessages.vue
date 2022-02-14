<template>
    <div v-if="hasMessages">
        <b-alert :show="history.isDeleted" variant="warning">
            {{ "This history has been deleted" | localize }}
        </b-alert>
        <b-alert :show="userOverQuota" variant="warning">
            {{
                "You are over your disk quota. Tool execution is on hold until your disk usage drops below your allocated quota."
                    | localize
            }}
        </b-alert>
    </div>
</template>

<script>
import { History } from "./model";

export default {
    props: {
        history: { type: History, required: true },
    },
    computed: {
        hasMessages() {
            return this.userOverQuota || history.isDeleted;
        },
    },
    data() {
        return {
            userOverQuota: false,
        };
    },
};
</script>
