<template>
    <div class="dropdown-menu" role="menu">
        <a
            class="rule-link dropdown-item"
            v-for="dateTime in getRules()"
            :key="dateTime"
            @click="loadSession(builder, dateTime)"
        >
            {{ dateTime }}
        </a>
    </div>
</template>

<script>
export default {
    props: {
        builder: {
            required: true,
        },
    },
    methods: {
        getRules() {
            var savedRules = [];
            var counter = 0;
            var regExpForSavedRules = /Saved Rule:.*/;
            for (var i = 0; i < localStorage.length; i++) {
                if (regExpForSavedRules.test(localStorage.key(i))) {
                    savedRules.push(localStorage.key(i));
                    counter++;
                    if (counter == 10) {
                        break;
                    }
                }
            }
            return savedRules;
        },
        loadSession(builder, dateTime) {
            var currentSession = JSON.parse(localStorage.getItem(dateTime));
            builder.rules = currentSession.rules;
            builder.mapping = currentSession.mapping;
        },
        saveSession(jsonRules) {
            var dateTimeString = "Saved Rule: " + new Date().toISOString();
            localStorage.setItem(dateTimeString, jsonRules);
        },
    },
};
</script>
