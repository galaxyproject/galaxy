import Backbone from "backbone";
import { getAppRoot } from "onload/loadConfig";

// ============================================================================
// TS GROUP RELATED MODELS

const Group = Backbone.Model.extend({
    urlRoot: `${getAppRoot()}api/groups`,
});

const Groups = Backbone.Collection.extend({
    url: `${getAppRoot()}api/groups`,

    model: Group,
});

export default {
    Group: Group,
    Groups: Groups,
};
