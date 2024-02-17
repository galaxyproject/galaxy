<script>
const NO_SECOND_ISO_DATE_REGEX = /\d{4}-[01]\d-[0-3]\dT[0-2]\d:[0-5]\d/;

export default {
    props: {
        prefix: {
            type: String,
            default: "galaxy_rules_",
        },
    },
    data: function () {
        return {
            savedRules: [],
        };
    },
    created() {
        let counter = 0;
        for (let i = 0; i < localStorage.length; i++) {
            if (localStorage.key(i).startsWith(this.prefix)) {
                const rule = localStorage.getItem(localStorage.key(i));
                if (rule) {
                    const key = localStorage.key(i);
                    const dateMatch = key.match(NO_SECOND_ISO_DATE_REGEX);
                    if (dateMatch) {
                        const dateTime = key.slice(dateMatch.index);
                        this.savedRules.push({
                            dateTime,
                            rule,
                        });
                        counter++;
                    }
                }
                if (counter == 10) {
                    break;
                }
            }
        }
    },
    methods: {
        saveSession(rule) {
            const dateTime = new Date().toISOString();
            const key = this.prefix + dateTime;
            localStorage.setItem(key, rule);
            this.savedRules.push({
                dateTime,
                rule,
            });
        },
    },
};
</script>
