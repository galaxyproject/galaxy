<template>
    <b-input-group>
        <b-input
            :placeholder="placeholder"
            v-model="queryInput"
            @input="delayQuery"
            @change="setQuery"
            @keydown.esc="setQuery()"
        />
        <b-input-group-append v-b-tooltip.hover title="clear search (esc)">
            <b-btn @click="setQuery()">
                <i class="fa fa-times" />
            </b-btn>
        </b-input-group-append>
    </b-input-group>
</template>
<script>
export default {
    props: {
        placeholder: {
            type: String,
            required: false,
            default: "Enter your search term here."
        },
        delay: {
            type: Number,
            required: false,
            default: 1000
        }
    },
    data() {
        return {
            queryInput: null,
            queryTimer: null,
            query: null
        };
    },
    methods: {
        clearTimer() {
            if (this.queryTimer) {
                clearTimeout(this.queryTimer);
            }
        },
        delayQuery(query) {
            this.clearTimer();
            if (query) {
                this.queryTimer = setTimeout(() => {
                    this.setQuery(query);
                }, this.delay);
            } else {
                this.setQuery(query);
            }
        },
        setQuery(queryNew) {
            this.clearTimer();
            if (this.query !== this.queryInput || this.query !== queryNew) {
                this.query = this.queryInput = queryNew;
                this.$emit("onChange", this.query);
            }
        }
    }
};
</script>
