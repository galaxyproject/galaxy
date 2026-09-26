export type HistoryUploadBlockReason = "archived" | "deleted";

type UploadTargetHistory = {
    archived?: boolean;
    deleted?: boolean;
};

const BLOCK_WARNING_BY_REASON: Record<HistoryUploadBlockReason, string> = {
    archived: "This history has been archived and cannot receive uploads. Select a different history to continue.",
    deleted: "This history has been deleted and cannot receive uploads. Select a different history to continue.",
};

const ACTION_ERROR_BY_REASON: Record<HistoryUploadBlockReason, string> = {
    archived: "Cannot upload: target history is archived. Select a different history and try again.",
    deleted: "Cannot upload: target history is deleted. Select a different history and try again.",
};

export function getHistoryUploadBlockReason(history?: UploadTargetHistory | null): HistoryUploadBlockReason | null {
    if (!history) {
        return null;
    }
    if (history.archived) {
        return "archived";
    }
    if (history.deleted) {
        return "deleted";
    }
    return null;
}

export function getHistoryUploadWarningMessage(reason?: HistoryUploadBlockReason | null): string {
    return reason ? BLOCK_WARNING_BY_REASON[reason] : "";
}

export function getHistoryUploadActionErrorMessage(reason?: HistoryUploadBlockReason | null): string {
    return reason ? ACTION_ERROR_BY_REASON[reason] : "";
}
