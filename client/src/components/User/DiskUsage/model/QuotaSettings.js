/** Wraps the Galaxy configuration and exposes only
 * quota related settings.
 */
export class QuotaSettings {
    constructor(config = {}) {
        this.config = config;
    }

    /** Whether disk quotas are enabled in this Galaxy instance.
     * @returns {Boolean}
     */
    get quotasEnabled() {
        return this.config.enable_quotas;
    }

    /** The URL linked for quota information in the UI.
     * @returns {String}
     */
    get quotasHelpUrl() {
        return this.config.quota_url;
    }

    /** Whether users are allowed to remove their datasets from disk immediately
     * (otherwise, datasets will be removed after a time period specified by an
     * administrator)
     * @returns {Boolean}
     */
    get canUserPurgeImmediately() {
        return this.config.allow_user_dataset_purge;
    }

    static create(config = {}) {
        return new QuotaSettings(config);
    }
}
