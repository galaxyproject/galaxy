import * as Backbone from "backbone";

export class TracksterUI extends Backbone.Model {
    constructor(options) {
        super(options);
    }

    initialize(baseURL) {
        this.baseURL = baseURL;
    }
}
