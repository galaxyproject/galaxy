/** en/main localization hash - for use with requirejs' i18n plugin */
define({
    // ----------------------------------------------------------------------------- masthead
    "Analyze Data": "Analizar datos",
    Workflow: "Flujo de trabajo",
    "Shared Data": "Datos compartidos",
    "Data Libraries": "Bibliotecas de datos",
    Histories: "Historias",
    Workflows: "Flujos de trabajo",
    Visualizations: "Visualizaciones",
    Pages: "Páginas",
    Visualization: "Visualización",
    "New Track Browser": "Nuevo navegador de pistas",
    "Saved Visualizations": "Visualizaciones Guardadas",
    "Interactive Environments": "Entornos Interactivos",
    Admin: "Administración",
    Help: "Ayuda",
    Support: "Apoyo",
    Search: "Buscar",
    "Mailing Lists": "Listas de correo",
    Videos: "Videos",
    Wiki: "Wiki",
    "How to Cite Galaxy": "Cómo citar a Galaxy",
    "Interactive Tours": "recorridos interactivos",
    User: "Usuario",
    Login: "Iniciar sesión",
    Register: "Registro",
    "Login or Register": "Iniciar sesión o Registrarse",
    "Logged in as": "Conectado como",
    Preferences: "Preferencias",
    "Custom Builds": "Construcciones personalizadas",
    Logout: "Cerrar sesión",
    "Saved Histories": "Historias Guardadas",
    "Saved Datasets": "Conjuntos de datos guardados",
    "Saved Pages": "Páginas guardadas",
    //Tooltip
    "Account and saved data": "Cuenta y datos guardados",
    "Account registration or login": "Registro de cuenta o inicio de sesión",
    "Support, contact, and community": "Apoyo, contacto y comunidad",
    "Administer this Galaxy": "Administrar esta galaxia",
    "Visualize datasets": "Visualizar conjuntos de datos",
    "Access published resources": "Acceso a los recursos publicados",
    "Chain tools into workflows": "Herramientas de cadena en flujos de trabajo",
    "Analysis home view": "Vista de inicio del análisis",
    // ---------------------------------------------------------------------------- histories
    // ---- history/options-menu
    "History Lists": "Listas de historia",
    // Saved histories is defined above.
    // "Saved Histories":
    //     false,
    "Histories Shared with Me": "Historias compartidas conmigo",
    "Current History": "Historia actual",
    "Create New": "Crear nuevo",
    "Copy History": "Historial de Copias",
    "Share or Publish": "Compartir o publicar",
    "Show Structure": "Mostrar Estructura",
    "Extract Workflow": "Extraer flujo de trabajo",
    // Delete is defined elsewhere, but is also in this menu.
    // "Delete":
    //     false,
    "Delete Permanently": "Borrar permanentemente",
    "Dataset Actions": "Acciones de conjuntos de datos",
    "Copy Datasets": "Conjuntos de datos de copia",
    "Dataset Security": "Seguridad del conjunto de datos",
    "Resume Paused Jobs": "Reanudar trabajos en pausa",
    "Collapse Expanded Datasets": "Contraer conjuntos de datos expandidos",
    "Unhide Hidden Datasets": "Mostrar conjuntos de datos ocultos",
    "Delete Hidden Datasets": "Eliminar conjuntos de datos ocultos",
    "Purge Deleted Datasets": "Eliminar los conjuntos de datos eliminados",
    Downloads: "Descargas",
    "Export Tool Citations": "Citas de herramientas de exportación",
    "Export History to File": "Exportar historial a archivo",
    "Other Actions": "Otras acciones",
    "Import from File": "Importar desde archivo",
    Webhooks: "WebHooks",
    // ---- history-model
    // ---- history-view
    "This history is empty": "Esta historia está vacía",
    "No matching datasets found": "No se encontraron conjuntos de datos coincidentes",
    "An error occurred while getting updates from the server":
        "Se ha producido un error al obtener actualizaciones desde el servidor",
    "Please contact a Galaxy administrator if the problem persists":
        "Póngase en contacto con un administrador de Galaxy si el problema persiste",
    //TODO:
    //"An error was encountered while <% where %>" :
    //false,
    "search datasets": "Conjuntos de datos de búsqueda",
    "You are currently viewing a deleted history!": "¡Actualmente estás viendo un historial eliminado!",
    "You are over your disk quota": "Has sobrepasado tu cuota de disco",
    "Tool execution is on hold until your disk usage drops below your allocated quota":
        "La ejecución de la herramienta está en espera hasta que el uso del disco caiga por debajo de la cuota asignada",
    All: "Todas",
    None: "Ninguna",
    "For all selected": "Para todos los seleccionados",
    // ---- history-view-edit
    "Edit history tags": "Editar etiquetas de historial",
    "Edit history Annotation": "Editar anotación de la historia",
    "Click to rename history": "Haga clic para cambiar el nombre del historial",
    // multi operations
    "Operations on multiple datasets": "Operaciones en conjuntos de datos múltiples",
    "Hide datasets": "Ocultar conjuntos de datos",
    "Unhide datasets": "Mostrar conjuntos de datos",
    "Delete datasets": "Borrar conjuntos de datos",
    "Undelete datasets": "Undelete datasets",
    "Permanently delete datasets": "Eliminar permanentemente conjuntos de datos",
    "This will permanently remove the data in your datasets. Are you sure?":
        "Esto eliminará permanentemente los datos de sus datasets. ¿Está seguro?",
    // ---- history-view-annotated
    Dataset: "Conjunto de datos",
    Annotation: "Anotación",
    // ---- history-view-edit-current
    "This history is empty. Click 'Get Data' on the left tool menu to start":
        "Este historial está vacío. Haga clic en 'Obtener datos' en el menú de herramientas de la izquierda para iniciar",
    "You must be logged in to create histories": "Debe haber iniciado sesión para crear historiales",
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
    "Unable to purge dataset": "No se puede purgar el dataset",
    // ---- hda-base
    // display button
    "Cannot display datasets removed from disk": "No se pueden mostrar conjuntos de datos eliminados del disco",
    "This dataset must finish uploading before it can be viewed":
        "Este conjunto de datos debe terminar de cargar antes de que se pueda ver",
    "This dataset is not yet viewable": "Este conjunto de datos aún no se puede ver",
    "View data": "Ver datos",
    // download button
    Download: "Descargar",
    "Download dataset": "Descargar dataset",
    "Additional files": "Archivos adicionales",
    // info/show_params
    "View details": "Ver detalles",
    // dataset states
    // state: new
    "This is a new dataset and not all of its data are available yet":
        "Este es un nuevo conjunto de datos y no todos sus datos están disponibles todavía",
    // state: noPermission
    "You do not have permission to view this dataset": "No tiene permiso para ver este conjunto de datos",
    // state: discarded
    "The job creating this dataset was cancelled before completion":
        "El trabajo que creó este conjunto de datos se canceló antes de completarse",
    // state: queued
    "This job is waiting to run": "Este trabajo está a la espera de ejecutar",
    // state: upload
    "This dataset is currently uploading": "Este conjunto de datos se está subiendo actualmente",
    // state: setting_metadata
    "Metadata is being auto-detected": "Los metadatos se detectan automáticamente",
    // state: running
    "This job is currently running": "Este trabajo se está ejecutando actualmente",
    // state: paused
    'This job is paused. Use the "Resume Paused Jobs" in the history menu to resume':
        'Este trabajo está en pausa Utilice la opción " Reanudar pausado Jobs " en el menú de historial para reanudar',
    // state: error
    "An error occurred with this dataset": "Se ha producido un error con este conjunto de datos",
    // state: empty
    "No data": "Sin datos",
    // state: failed_metadata
    "An error occurred setting the metadata for this dataset":
        "Se ha producido un error al establecer los metadatos de este conjunto de datos",
    // ajax error prefix
    "There was an error getting the data for this dataset":
        "Hubo un error al obtener los datos de este conjunto de datos",
    // purged'd/del'd msg
    "This dataset has been deleted and removed from disk":
        "Este conjunto de datos ha sido eliminado y eliminado del disco",
    "This dataset has been deleted": "Este conjunto de datos ha sido eliminado",
    "This dataset has been hidden": "Este conjunto de datos se ha ocultado",
    format: "Formato",
    database: "base de datos",
    // ---- hda-edit
    "Edit attributes": "Editar atributos",
    "Cannot edit attributes of datasets removed from disk":
        "No se pueden editar los atributos de conjuntos de datos eliminados del disco",
    "Undelete dataset to edit attributes": "Undelete el conjunto de datos para editar atributos",
    "This dataset must finish uploading before it can be edited":
        "Este conjunto de datos debe terminar de cargar antes de que pueda ser editado",
    "This dataset is not yet editable": "Este conjunto de datos aún no es editable",
    Delete: "Borrar",
    "Dataset is already deleted": "El conjunto de datos ya se ha eliminado",
    "View or report this error": "Ver o informar de este error",
    "Run this job again": "Ejecutar este trabajo de nuevo",
    Visualize: "Visualizar",
    "Visualize in": "Visualizar en",
    "Undelete it": "Undelete it",
    "Permanently remove it from disk": "Eliminar permanentemente del disco",
    "Unhide it": "Mostrarlo",
    "You may be able to": "Usted puede ser capaz de",
    "set it manually or retry auto-detection": "Configurar manualmente o volver a intentar la detección automática",
    "Edit dataset tags": "Editar etiquetas de dataset",
    "Edit dataset annotation": "Editar anotación del conjunto de datos",
    // ---------------------------------------------------------------------------- misc. MVC
    Tags: "Tags",
    "Edit annotation": "Editar anotación",
});
