/** Button variant with waiting and progress tracking. */
<template>
    <button
        class="ui-button-default"
        v-bind:class="[waiting ? 'disabled' : '', variantClass]"
        type="button"
        v-on:click="$emit('click')"
    >
        <i class="icon fa" v-bind:class="iconClass"> </i>
        <span class="title"> {{ currentText }} </span>
        <div class="progress" v-if="percentage != -1">
            <div class="progress-bar" v-bind:style="{ width: progressWidth }"></div>
        </div>
    </button>
</template>

<script>
export default {
    props: {
        title: {
            type: String,
            default: ""
        },
        icon: {
            type: String,
            deafult: ""
        },
        percentage: {
            type: Number,
            default: -1
        },
        waiting: {
            type: Boolean,
            default: false
        },
        waitText: {
            type: String,
            default: "Sending..."
        },
        variant: {
            type: String,
            default: "info"
        }
    },
    computed: {
        progressWidth() {
            return `${this.percentage}%`;
        },
        variantClass() {
            return `btn btn-${this.variant}`;
        },
        iconClass() {
            if (this.waiting) {
                return "fa-spinner fa-spin mr-1";
            } else {
                return this.icon + " mr-1";
            }
        },
        currentText() {
            if (this.waiting) {
                return this.waitText;
            } else {
                return this.title;
            }
        }
    }
};
</script>
