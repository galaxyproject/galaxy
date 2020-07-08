<template>
    <div>
        <span class="note" v-if="note">
            {{ note }}<span v-if="loading">.<span class="blinking">..</span></span>
        </span>
        <b-progress>
            <b-progress-bar variant="secondary" :value="infoProgress * 100" :label="infoMessage"/>
            <b-progress-bar variant="info" :value="runningProgress * 100" :label="runningMessage"/>
            <b-progress-bar variant="success" :value="okProgress * 100" :label="okMessage"/>
            <b-progress-bar variant="warning" :value="newProgress * 100" :label="newMessage"/>
            <b-progress-bar variant="danger" :value="errorProgress * 100" :label="errorMessage"/>
        </b-progress>
    </div>
</template>
<script>
// Not really a very generic ProgressBar - consider renaming to StateProgressBar.
export default {
    props: {
        note: { type: String, default: null },
        loading: { type: Boolean, default: false },
        infoProgress: { type: Number, default: 0.0 },
        infoMessage: { type: String, default: null },
        okProgress: { type: Number, default: 0.0 },
        okMessage: { type: String, default: null },
        runningProgress: { type: Number, default: 0.0 },
        runningMessage: { type: String, default: null },
        newProgress: { type: Number, default: 0.0 },
        newMessage: { type: String, default: null },
        errorProgress: { type: Number, default: 0.0 },
        errorMessage: { type: String, default: null },
    }
};
</script>
