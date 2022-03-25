/** en/main localization hash - for use with requirejs' i18n plugin */
define({
    // ----------------------------------------------------------------------------- masthead
    "Analyze Data": "Daten analysieren",
    Workflow: "Arbeitsablauf",
    "Shared Data": "Gemeinsame Daten",
    "Data Libraries": "Datenbibliotheken",
    Histories: "Geschichten",
    Workflows: "Workflows",
    Visualizations: "Visualisierungen",
    Pages: "Seiten",
    Visualization: "Visualisierung",
    "New Track Browser": "Neuer Track Browser",
    "Saved Visualizations": "Gespeicherte Visualisierungen",
    Admin: "Administrator",
    Help: "Hilfe",
    Support: "Unterstützung",
    Search: "Suche",
    "Mailing Lists": "Mailinglisten",
    Videos: "Videos",
    "Community Hub": "Community Hub",
    "How to Cite Galaxy": "Wie man Galaxie zitiert",
    User: "Benutzer",
    Login: "Anmeldung",
    Register: "Neu registrieren",
    "Login or Register": "Einloggen oder Registrieren",
    "Logged in as": "Angemeldet als",
    Preferences: "Präferenzen",
    "Custom Builds": "Custom Builds",
    Logout: "Ausloggen",
    "Saved Histories": "Gespeicherte Geschichten",
    "Saved Datasets": "Gespeicherte Datasets",
    "Saved Pages": "Gespeicherte Seiten",
    //Tooltip
    "Account and saved data": "Konto und gespeicherte Daten",
    "Account registration or login": "Konto Registrierung oder Login",
    "Support, contact, and community": "Unterstützung, Kontakt und Community",
    "Administer this Galaxy": "Verwalte diese Galaxie",
    "Visualize datasets": "Visualisieren von Datensätzen",
    "Access published resources": "Zugriff auf veröffentlichte Ressourcen",
    "Chain tools into workflows": "Kettenwerkzeuge in Workflows",
    "Analysis home view": "Analyse home view",
    // ---------------------------------------------------------------------------- histories
    // ---- history/options-menu
    "History Lists": "History Lists",
    // Saved histories is defined above.
    // "Saved Histories":
    //     false,
    "Histories Shared with Me": "Geschichten mit mir geteilt",
    "Current History": "Aktuelle Geschichte",
    "Create New": "Erstelle neu",
    "Copy History": "Geschichte kopieren",
    "Share or Publish": "Teilen oder veröffentlichen",
    "Show Structure": "Struktur anzeigen",
    "Extract Workflow": "Workflow extrahieren",
    // Delete is defined elsewhere, but is also in this menu.
    // "Delete":
    //     false,
    "Delete Permanently": "Dauerhaft löschen",
    "Dataset Actions": "Datensatzaktionen",
    "Copy Datasets": "Datensätze kopieren",
    "Dataset Security": "Datensatz Sicherheit",
    "Resume Paused Jobs": "Fortsetzen pausierte Jobs",
    "Collapse Expanded Datasets": "Collapse Expanded Datasets",
    "Unhide Hidden Datasets": "Hidden Datasets verstecken",
    "Delete Hidden Datasets": "Hidden Datasets löschen",
    "Purge Deleted Datasets": "Gelöschte Datasets löschen",
    Downloads: "Downloads",
    "Export Tool Citations": "Export Tool Zitate",
    "Export History to File": "Export History to File",
    "Other Actions": "Andere Aktionen",
    "Import from File": "Import aus Datei",
    Webhooks: "Webhooks",
    // ---- history-model
    // ---- history-view
    "This history is empty": "Diese Geschichte ist leer",
    "No matching datasets found": "Keine passenden Datensätze gefunden",
    "An error occurred while getting updates from the server":
        "Ein Fehler ist aufgetreten beim Aktualisieren vom Server",
    "Please contact a Galaxy administrator if the problem persists":
        "Bitte wenden Sie sich an einen Galaxy-Administrator, wenn das Problem weiterhin besteht",
    //TODO:
    //"An error was encountered while <% where %>" :
    //false,
    "search datasets": "Suchdatensätze",
    "You are currently viewing a deleted history!": "Du siehst derzeit einen gelöschten Verlauf!",
    "You are over your disk quota": "Du bist über dein Festplatten-Kontingent",
    "Tool execution is on hold until your disk usage drops below your allocated quota":
        "Tool-Ausführung ist in der Warteschleife, bis Ihre Datenträgerverwendung unter Ihrem zugeteilten Kontingent fällt",
    All: "Alle",
    None: "Keiner",
    "For all selected": "Für alle ausgewählt",
    // ---- history-view-edit
    "Edit history tags": "Geschichte bearbeiten",
    "Edit history annotation": "Historie bearbeiten",
    "Click to rename history": "Klicken Sie hier, um den Verlauf umzubenennen",
    // multi operations
    "Operations on multiple datasets": "Operationen auf mehreren Datensätzen",
    "Hide datasets": "Datensätze ausblenden",
    "Unhide datasets": "Datasets einblenden",
    "Delete datasets": "Datensätze löschen",
    "Undelete datasets": "Undelete-Datasets",
    "Permanently delete datasets": "Datensätze dauerhaft löschen",
    "This will permanently remove the data in your datasets. Are you sure?":
        "Das wird endgültig die Daten in deinen Datasets entfernen. Bist du sicher?",
    // ---- history-view-annotated
    Dataset: "Dataset",
    Annotation: "Annotation",
    // ---- history-view-edit-current
    "This history is empty. Click 'Get Data' on the left tool menu to start":
        "Diese Geschichte ist leer. Klicken Sie auf 'Get Data' im linken Tool-Menü, um",
    "You must be logged in to create histories": "Du musst eingeloggt sein, um Geschichten zu schaffen",
    //TODO:
    //"You can <% loadYourOwn %> or <% externalSource %>" :
    //false,
    //"load your own data" :
    //false,
    //"get data from an external source" :
    //false,

    // these aren't in zh/ginga.po and the template doesn't localize
    //"Include Deleted Datasets" :
    //false,
    //"Include Hidden Datasets" :
    //false,

    // ---------------------------------------------------------------------------- datasets
    // ---- hda-model
    "Unable to purge dataset": "Dataset kann nicht gelöscht werden",
    // ---- hda-base
    // display button
    "Cannot display datasets removed from disk": "Datasets können nicht von der Festplatte entfernt werden",
    "This dataset must finish uploading before it can be viewed":
        "Dieser Datensatz muss das Hochladen beenden, bevor es angezeigt werden kann",
    "This dataset is not yet viewable": "Dieser Datensatz ist noch nicht sichtbar",
    "View data": "Daten anzeigen",
    // download button
    Download: "Herunterladen",
    "Download dataset": "Dataset herunterladen",
    "Additional files": "Zusätzliche Dateien",
    // info/show_params
    "View details": "Details anzeigen",
    // dataset states
    // state: new
    "This is a new dataset and not all of its data are available yet":
        "Dies ist ein neuer Datensatz und nicht alle seine Daten sind noch verfügbar",
    // state: noPermission
    "You do not have permission to view this dataset": "Sie haben keine Berechtigung, diesen Datensatz anzuzeigen",
    // state: discarded
    "The job creating this dataset was cancelled before completion":
        "Der Job, der diesen Datensatz erstellt hat, wurde vor der Fertigstellung abgebrochen",
    // state: queued
    "This job is waiting to run": "Dieser Job wartet darauf, zu rennen",
    // state: upload
    "This dataset is currently uploading": "Dieser Datensatz lädt derzeit",
    // state: setting_metadata
    "Metadata is being auto-detected": "Metadaten werden automatisch erkannt",
    // state: running
    "This job is currently running": "Dieser Job läuft derzeit",
    // state: paused
    'This job is paused. Use the "Resume Paused Jobs" in the history menu to resume':
        'Dieser Job wird pausiert. Verwenden Sie die "Resume Paused Jobs " im Verlaufsmenü, um',
    // state: error
    "An error occurred with this dataset": "Ein Fehler ist mit diesem Datensatz aufgetreten",
    // state: empty
    "No data": "Keine Daten",
    // state: failed_metadata
    "An error occurred setting the metadata for this dataset":
        "Ein Fehler ist aufgetreten Einstellung der Metadaten für diese Datenmenge",
    // ajax error prefix
    "There was an error getting the data for this dataset":
        "Es gab einen Fehler, der die Daten für diesen Datensatz bekam",
    // purged'd/del'd msg
    "This dataset has been deleted and removed from disk":
        "Dieser Datensatz wurde gelöscht und von der Festplatte entfernt",
    "This dataset has been deleted": "Dieser Datensatz wurde gelöscht",
    "This dataset has been hidden": "Dieser Datensatz wurde ausgeblendet",
    format: "Format",
    database: "Datenbank",
    // ---- hda-edit
    "Edit attributes": "Attribute bearbeiten",
    "Cannot edit attributes of datasets removed from disk":
        "Kann keine Attribute von Datasets aus dem Datenträger entfernen",
    "Undelete dataset to edit attributes": "Undelete-Dataset zum Bearbeiten von Attributen",
    "This dataset must finish uploading before it can be edited":
        "Dieser Datensatz muss das Hochladen beenden, bevor es bearbeitet werden kann",
    "This dataset is not yet editable": "Dieser Datensatz ist noch nicht bearbeitbar",
    Delete: "Löschen",
    "Dataset is already deleted": "Dataset ist bereits gelöscht",
    "View or report this error": "Diesen Fehler anzeigen oder melden",
    "Run this job again": "Führen Sie diesen Job wieder",
    Visualize: "Visualisieren",
    "Visualize in": "Visualize in",
    "Undelete it": "Untelete it",
    "Permanently remove it from disk": "Permanent aus der Scheibe entfernen",
    "Unhide it": "Ausblenden",
    "You may be able to": "Sie können in der Lage sein",
    "set it manually or retry auto-detection": "Manuell einstellen oder Auto-Erkennung wiederholen",
    "Edit dataset tags": "Dataset-Tags bearbeiten",
    "Edit dataset annotation": "Datensatz-Annotation bearbeiten",
    // ---------------------------------------------------------------------------- misc. MVC
    Tags: "Variablen",
    "Edit annotation": "Anmerkung bearbeiten",
});
