function logSentryEvent(type, id) {
    Galaxy.Sentry?.captureMessage(`TEST - HelpMode - ${type} - ${id}`, {
        extra: {
            sandbox: true,
            feature: "HelpMode",
            eventType: type,
            eventId: id,
        },
    })
}
