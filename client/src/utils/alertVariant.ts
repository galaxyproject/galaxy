// Server messages and the message_box_class option use Galaxy's own status names.
const GALAXY_STATUS_VARIANTS: Record<string, string> = {
    done: "success",
    error: "danger",
};

/**
 * Translates a Galaxy message status (done, error, info, warning) into a GAlert variant.
 * Other values pass through; an unset status leaves GAlert at its default.
 */
export function alertVariant(status?: string | null): string | undefined {
    if (!status) {
        return undefined;
    }
    return GALAXY_STATUS_VARIANTS[status] ?? status;
}
