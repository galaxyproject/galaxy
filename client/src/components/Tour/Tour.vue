<template>
    <CurrentUser v-slot="{ user }" class="d-flex flex-column">
        <UserHistories v-if="user" v-slot="{ currentHistory, handlers, historiesLoading }" :user="user">
            <div v-if="historiesLoading">computing tour requirements...</div>
            <b-modal
                id="tour-requirement-unment"
                v-model="showRequirementDialog"
                static
                ok-only
                hide-header
                v-else-if="loginRequired(user)">
                <b-alert show variant="danger"> You must login to Galaxy to use this tour. </b-alert>
            </b-modal>
            <b-modal
                id="tour-requirement-unment"
                v-model="showRequirementDialog"
                static
                ok-only
                hide-header
                v-else-if="adminRequired(user)">
                <b-alert show variant="danger"> You must be an admin user to use this tour. </b-alert>
            </b-modal>
            <b-modal
                id="tour-requirement-unment"
                v-model="showRequirementDialog"
                static
                ok-only
                hide-header
                v-else-if="newHistoryRequired(currentHistory, handlers)">
                <b-alert show variant="danger">
                    This tour is designed to run on a new history, please create a new history before running it.
                    <a @click.prevent="handlers.createNewHistory()">Click here</a> to create a new history.
                </b-alert>
            </b-modal>
            <TourStep
                v-else-if="currentStep"
                :key="currentIndex"
                :step="currentStep"
                :is-playing="isPlaying"
                :is-last="isLast"
                @next="next"
                @end="end"
                @play="play" />
        </UserHistories>
    </CurrentUser>
</template>

<script>
import TourStep from "./TourStep";
import CurrentUser from "components/providers/CurrentUser";
import UserHistories from "components/providers/UserHistories";

// popup display duration when auto-playing the tour
const playDelay = 3000;

export default {
    components: {
        TourStep,
        CurrentUser,
        UserHistories,
    },
    props: {
        steps: {
            type: Array,
            required: true,
        },
        requirements: {
            type: Array,
            required: true,
        },
    },
    data() {
        return {
            currentIndex: -1,
            isPlaying: false,
            showRequirementDialog: true,
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
        hasBegun() {
            return this.currentIndex >= 1;
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
        loginRequired(user) {
            return !this.hasBegun && this.requirements.indexOf("logged_in") >= 0 && user.isAnonymous;
        },
        adminRequired(user) {
            return !this.hasBegun && this.requirements.indexOf("admin") >= 0 && !user.is_admin;
        },
        newHistoryRequired(history) {
            if (this.hasBegun) {
                return false;
            }
            const hasNewNistoryRequirement = this.requirements.indexOf("new_history") >= 0;
            if (!hasNewNistoryRequirement) {
                return false;
            } else if (history && history.size != 0) {
                // TODO: better estimate for whether the history is new.
                return true;
            } else {
                return false;
            }
        },
        createNewHistory(handlers) {
            handlers.createNewHistory();
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
