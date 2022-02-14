<template functional>
    <div v-if="dataset">
        <p v-localize>This job is paused. Use the "Resume Paused Jobs" in the history menu to resume.</p>
        <div v-if="dataset.misc_info">
            <span>{{ props.dataset.misc_info }}</span>
        </div>
    </div>
</template>
