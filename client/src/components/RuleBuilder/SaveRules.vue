<script>
import { getGalaxyInstance } from "app";
export default {
    props: {
        prefix: {
            type: String,
            default: "galaxy_rules_",
        },
        user: {
            type: String,
            default: getGalaxyInstance() ? getGalaxyInstance().user.id : "",
        },
    },
    data: function () {
        return {
            savedRules: [],
        };
    },
    created() {
        let counter = 0;
        if (this.user == null) {
            return;
        } else {
            for (let i = 0; i < localStorage.length; i++) {
                if (localStorage.key(i).startsWith(this.prefix + this.user)) {
                    var savedSession = localStorage.getItem(localStorage.key(i));
                    if (savedSession) {
                        var key = localStorage.key(i);
                        this.savedRules.push({
                            dateTime: key.substring(this.prefix.length + this.user.length),
                            rule: savedSession,
                        });
                    }
                    counter++;
                    if (counter == 10) {
                        break;
                    }
                }
            }
        }
    },
    methods: {
        saveSession(jsonRulesString) {
            var dateTimeString = new Date().toISOString();
            var key = this.prefix + this.user + dateTimeString;
            localStorage.setItem(key, jsonRulesString);
            this.savedRules.push({
                dateTime: dateTimeString,
                rule: jsonRulesString,
            });
        },
    },
};
</script>
