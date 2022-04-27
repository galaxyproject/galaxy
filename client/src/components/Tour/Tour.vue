<template>
    <TourStep
        v-if="currentStep"
        :key="currentIndex"
        :step="currentStep"
        :is-playing="isPlaying"
        :is-last="isLast"
        @next="next"
        @end="end"
        @play="play" />
</template>

<script>
import TourStep from "./TourStep";

// popup display duration when auto-playing the tour
const playDelay = 3000;

export default {
    components: {
        TourStep,
    },
    props: {
        steps: {
            type: Array,
            required: true,
        },
    },
    data() {
        return {
            currentIndex: -1,
            isPlaying: false,
        };
    },
    computed: {
        currentStep() {
            return this.steps[this.currentIndex];
        },
        numberOfSteps() {
            return this.steps.length;
        },
        isLast() {
            return this.currentIndex === this.steps.length - 1;
        },
    },
    beforeDestroy() {
        window.removeEventListener("keyup", this.handleKeyup);
    },
    mounted() {
        this.start();
    },
    methods: {
        start() {
            window.addEventListener("keyup", this.handleKeyup);
            this.currentIndex = 0;
        },
        play(isPlaying) {
            this.isPlaying = isPlaying;
            if (this.isPlaying) {
                this.next();
            }
        },
        async next() {
            // do post-actions
            if (this.currentStep && this.currentStep.onNext) {
                await this.currentStep.onNext();
            }
            // do pre-actions
            const nextIndex = this.currentIndex + 1;
            if (nextIndex < this.numberOfSteps && this.currentIndex !== -1) {
                const nextStep = this.steps[nextIndex];
                if (nextStep.onBefore) {
                    await nextStep.onBefore();
                    // automatically continues to next step if enabled
                    if (this.isPlaying) {
                        setTimeout(() => {
                            if (this.isPlaying) {
                                this.next();
                            }
                        }, playDelay);
                    }
                }
            }
            // go to next step
            this.currentIndex = nextIndex;
        },
        end() {
            this.currentIndex = -1;
            this.isPlaying = false;
        },
        handleKeyup(e) {
            switch (e.keyCode) {
                case 39:
                    this.next();
                    break;
                case 27:
                    this.end();
                    break;
            }
        },
    },
};
</script>
