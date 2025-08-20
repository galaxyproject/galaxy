<template>
    <div
        ref="tour-element"
        class="tour-element"
        :class="{ 'tour-element-sticky': !targetElementVisible, 'tour-has-title': !!step.title }">
        <div v-if="step.title" class="tour-header">
            <div class="tour-title" v-html="step.title"></div>
        </div>
        <div v-if="step.content" class="tour-content" v-html="step.content" />
        <div class="tour-buttons">
            <div v-if="isLast">
                <button class="tour-button tour-end" @click.prevent="$emit('end')">Close</button>
            </div>
            <div v-else-if="isPlaying">
                <button
                    v-if="waitingOnElement"
                    v-b-tooltip.hover
                    :title="`Waiting for ${waitingOnElement}`"
                    class="btn btn-link btn-sm">
                    <FontAwesomeIcon :icon="faSpinner" spin />
                </button>
                <button class="tour-button tour-stop" @click.prevent="$emit('play', false)">Stop</button>
            </div>
            <div v-else>
                <button
                    v-if="waitingOnElement"
                    v-b-tooltip.hover
                    :title="`Waiting for ${waitingOnElement}`"
                    class="btn btn-link btn-sm">
                    <FontAwesomeIcon :icon="faSpinner" spin />
                </button>
                <button class="tour-button tour-end" @click.prevent="$emit('end')">End Tour</button>
                <button class="tour-button tour-play" @click.prevent="$emit('play', true)">Play</button>
                <button class="tour-button tour-next" @click.prevent="$emit('next')">Continue</button>
            </div>
        </div>
        <div v-if="targetElement" class="tour-arrow" data-popper-arrow />
    </div>
</template>

<script>
import { faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { createPopper } from "@popperjs/core";

export default {
    components: {
        FontAwesomeIcon,
    },
    props: {
        step: {
            type: Object,
        },
        isPlaying: {
            type: Boolean,
        },
        isLast: {
            type: Boolean,
        },
        waitingOnElement: {
            type: String,
            default: null,
        },
    },
    data() {
        return {
            faSpinner,
        };
    },
    computed: {
        targetElement() {
            if (this.step.element) {
                return document.querySelector(this.step.element);
            }
            return null;
        },
        targetElementVisible() {
            const el = this.targetElement;
            if (el) {
                const rect = el.getBoundingClientRect();
                return rect && rect.width > 0 && rect.height > 0;
            }
            return false;
        },
    },
    mounted() {
        this.createStep();
    },
    methods: {
        createStep() {
            if (this.targetElement && this.targetElementVisible) {
                createPopper(this.targetElement, this.$refs["tour-element"], {
                    modifiers: [
                        {
                            name: "preventOverflow",
                            options: {
                                altAxis: true,
                                tether: false,
                                padding: 20,
                            },
                        },
                    ],
                    strategy: "absolute",
                    placement: "auto",
                });
            }
        },
    },
};
</script>
