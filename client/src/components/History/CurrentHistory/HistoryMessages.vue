<template>
    <div v-if="hasMessages" class="mx-3 my-2">
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
export default {
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
