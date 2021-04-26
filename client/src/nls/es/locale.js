/** en/main localization hash - for use with requirejs' i18n plugin */

define({
    // ----------------------------------------------------------------------------- masthead

    "Analyze Data": "Analizar Datos",

    Workflow: "Flujo de Trabajo",

    "Shared Data": "Datos Compartidos",

    "Data Libraries": "Bibliotecas de Datos",

    Histories: "Historiales",

    Workflows: "Flujos de Trabajo",

    Visualizations: "Visualizaciones",

    Pages: "Páginas",

    Visualization: "Visualización",

    "New Track Browser": "Nuevo Navegador de Pistas",

    "Saved Visualizations": "Visualizaciones Guardadas",

    "Interactive Environments": "Entornos Interactivos",

    Admin: "Administración",

    Help: "Ayuda",

    Support: "Soporte",

    Search: "Buscar",

    "Mailing Lists": "Listas de Correo",

    Videos: "Videos",

    Wiki: "Wiki",

    "How to Cite Galaxy": "Cómo citar Galaxy",

    "Interactive Tours": "Tours Interactivos",

    User: "Usuario",

    Login: "Iniciar sesión",

    Register: "Registro",

    "Login or Register": "Iniciar sesión o Registrarse",

    "Logged in as": "Se ha conectado como",

    Preferences: "Preferencias",

    "Custom Builds": "Construcciones personalizadas",

    Logout: "Cerrar Sesión",

    "Saved Histories": "Historiales Guardados",

    "Saved Datasets": "Conjuntos de Datos Guardados",

    "Saved Pages": "Páginas Guardadas",

    //Tooltip

    "Account and saved data": "Cuenta y Datos Guardados",

    "Account registration or login": "Crear Cuenta o Iniciar Sesión",

    "Support, contact, and community": "Apoyo, contacto y comunidad",

    "Administer this Galaxy": "Administrar esta instancia de Galaxy",

    "Visualize datasets": "Visualizar conjuntos de datos",

    "Access published resources": "Acceder a los recursos publicados",

    "Chain tools into workflows": "Encadenar herramientas en flujos de trabajo",

    "Analysis home view": "Vista de inicio del análisis",

    // ---------------------------------------------------------------------------- histories

    // ---- history/options-menu

    "History Lists": "Listas de historiales",

    // Saved histories is defined above.

    // "Saved Histories":

    //     false,

    "Histories Shared with Me": "Historiales compartidos conmigo",

    "Current History": "Historial actual",

    "Create New": "Crear nuevo",

    "Copy History": "Copiar Historial",

    "Share or Publish": "Compartir o Publicar",

    "Show Structure": "Mostrar Estructura",

    "Extract Workflow": "Extraer Flujo de Trabajo",

    // Delete is defined elsewhere, but is also in this menu.

    // "Delete":

    //     false,

    "Delete Permanently": "Borrar Permanentemente",

    "Dataset Actions": "Acciones de Conjuntos de Datos",

    "Copy Datasets": "Copiar Conjuntos de Datos",

    "Dataset Security": "Seguridad del Conjunto de Datos",

    "Resume Paused Jobs": "Reanudar Trabajos en Pausa",

    "Collapse Expanded Datasets": "Contraer Conjuntos de Datos Expandidos",

    "Unhide Hidden Datasets": "Mostrar Conjuntos de Datos Ocultos",

    "Delete Hidden Datasets": "Eliminar Conjuntos de Datos Ocultos",

    "Purge Deleted Datasets": "Eliminar Definitivamente los Conjuntos de Datos Eliminados",

    Downloads: "Descargas",

    "Export Tool Citations": "Exportar las Citas de la Herramienta",

    "Export History to File": "Exportar Historial a un Archivo",

    "Other Actions": "Otras Acciones",

    "Import from File": "Importar desde Archivo",

    Webhooks: "WebHooks",

    // ---- history-model

    // ---- history-view

    "This history is empty": "Este historial está vacío",

    "No matching datasets found": "No se encontraron conjuntos de datos coincidentes",

    "An error occurred while getting updates from the server":
        "Se ha producido un error al obtener actualizaciones desde el servidor",

    "Please contact a Galaxy administrator if the problem persists":
        "Por favor, contacte a un administrador de Galaxy si el problema persiste",

    //TODO:

    //"An error was encountered while <% where %>" :

    //false,

    "search datasets": "buscar conjuntos de datos",

    "You are currently viewing a deleted history!": "¡Estás viendo un historial eliminado!",

    "You are over your disk quota": "Has sobrepasado tu espacio disponible de disco",

    "Tool execution is on hold until your disk usage drops below your allocated quota":
        "La ejecución de la herramienta está en espera hasta que el uso del disco caiga por debajo de tu espacio de disco disponible",

    All: "Todas",

    None: "Ninguna",

    "For all selected": "Para todos los seleccionados",

    // ---- history-view-edit

    "Edit history tags": "Editar etiquetas de historial",

    "Edit history Annotation": "Editar anotación del historial",

    "Click to rename history": "Haz clic para cambiar el nombre del historial",

    // multi operations

    "Operations on multiple datasets": "Operaciones en conjuntos de datos múltiples",

    "Hide datasets": "Ocultar conjuntos de datos",

    "Unhide datasets": "Mostrar conjuntos de datos",

    "Delete datasets": "Borrar conjuntos de datos",

    "Undelete datasets": "Recuperar conjuntos de datos",

    "Permanently delete datasets": "Eliminar permanentemente conjuntos de datos",

    "This will permanently remove the data in your datasets. Are you sure?":
        "Esta acción eliminará datos permanentemente. ¿Estás seguro que deseas continuar?",

    // ---- history-view-annotated

    Dataset: "Conjunto de datos",

    Annotation: "Anotación",

    // ---- history-view-edit-current

    "This history is empty. Click 'Get Data' on the left tool menu to start":
        "Este historial está vacío. Haz clic en 'Obtener datos' en el menú de herramientas de la izquierda para iniciar",

    "You must be logged in to create histories": "Debes haber iniciado sesión para crear historiales",

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

    "Unable to purge dataset": "No se puede eliminar permanentemente el conjunto de datos",

    // ---- hda-base

    // display button

    "Cannot display datasets removed from disk":
        "No se pueden mostrar conjuntos de datos que han sido eliminados del disco",

    "This dataset must finish uploading before it can be viewed":
        "Este conjunto de datos debe terminar de cargar antes de visualizarlo",

    "This dataset is not yet viewable": "Este conjunto de datos aún no se puede ver",

    "View data": "Ver datos",

    // download button

    Download: "Descargar",

    "Download dataset": "Descargar conjunto de datos",

    "Additional files": "Archivos adicionales",

    // info/show_params

    "View details": "Ver detalles",

    // dataset states

    // state: new

    "This is a new dataset and not all of its data are available yet":
        "Este es un nuevo conjunto de datos y aún no está completamente disponible",

    // state: noPermission

    "You do not have permission to view this dataset": "No tienes permiso para ver este conjunto de datos",

    // state: discarded

    "The job creating this dataset was cancelled before completion":
        "El trabajo que estaba creando este conjunto de datos se canceló antes de completarse",

    // state: queued

    "This job is waiting to run": "Este trabajo está a la espera de ser ejecutado",

    // state: upload

    "This dataset is currently uploading": "Este conjunto de datos se está cargando actualmente",

    // state: setting_metadata

    "Metadata is being auto-detected": "Se han detectado metadatos automáticamente",

    // state: running

    "This job is currently running": "Este trabajo se está siendo ejecutando actualmente",

    // state: paused

    'This job is paused. Use the "Resume Paused Jobs" in the history menu to resume':
        'Este trabajo está en pausa. Utilice la opción "Reanudar trabajos en pausa" en el menú de historial para reanudar',

    // state: error

    "An error occurred with this dataset": "Se ha producido un error con este conjunto de datos",

    // state: empty

    "No data": "Sin datos",

    // state: failed_metadata

    "An error occurred setting the metadata for this dataset":
        "Se ha producido un error al establecer los metadatos de este conjunto de datos",

    // ajax error prefix

    "There was an error getting the data for this dataset":
        "Hubo un error al extraer el contenido de este conjunto de datos",

    // purged'd/del'd msg

    "This dataset has been deleted and removed from disk":
        "Este conjunto de datos ha sido eliminado permanentemente del disco",

    "This dataset has been deleted": "Este conjunto de datos ha sido eliminado",

    "This dataset has been hidden": "Este conjunto de datos ha sido ocultado",

    format: "formato",

    database: "base de datos",

    // ---- hda-edit

    "Edit attributes": "Editar atributos",

    "Cannot edit attributes of datasets removed from disk":
        "No se pueden editar los atributos de conjuntos de datos que han sido eliminados del disco",

    "Undelete dataset to edit attributes": "Recuperar el conjunto de datos para editar atributos",

    "This dataset must finish uploading before it can be edited":
        "Este conjunto de datos debe terminar de cargar antes de que pueda ser editado",

    "This dataset is not yet editable": "Este conjunto de datos aún no se puede editar",

    Delete: "Borrar",

    "Dataset is already deleted": "El conjunto de datos ya ha sido eliminado",

    "View or report this error": "Ver o informar de este error",

    "Run this job again": "Ejecutar este trabajo de nuevo",

    Visualize: "Visualizar",

    "Visualize in": "Visualizar en",

    "Undelete it": "Recuperar",

    "Permanently remove it from disk": "Eliminar permanentemente del disco",

    "Unhide it": "Mostrar",

    "You may be able to": "Podrás",

    "set it manually or retry auto-detection": "configurar manualmente o volver a intentar la detección automática",

    "Edit dataset tags": "Editar etiquetas del conjunto de datos",

    "Edit dataset annotation": "Editar anotación del conjunto de datos",

    // ---------------------------------------------------------------------------- misc. MVC

    Tags: "Etiquetas",

    "Edit annotation": "Editar anotación",

    "Tool Help": "Ayuda de herramienta",

    // ---------------------------------------------------------------------------- admin
    "Reset passwords": "Restablecer contraseña",
    "Search Tool Shed": "Buscar en el Tool Shed",
    "Monitor installing repositories": "Monitorear instalación de repositorios",
    "Manage installed tools": "Administrar herramientas instaladas",
    "Reset metadata": "Reconfigurar metadatos",
    "Download local tool": "Descargar herramienta local",
    "Tool lineage": "Linaje de herramientas",
    "Reload a tool's configuration": "Volver a cargar la configuración de una herramienta",
    "Review tool migration stages": "Revisar las etapas de migración de la herramienta",
    "View Tool Error Logs": "Ver registros de error de la herramienta",
    "Manage Allowlist": "Administrar lista de permisos",
    "Manage Tool Dependencies": "Administrar dependencias de herramienta",
    Users: "Usuarios",
    Groups: "Grupos",
    "API keys": "Llaves API",
    "Impersonate a user": "Acceder como otro usuario",
    Data: false,
    Quotas: false,
    Roles: false,
    "Local data": "Datos locales",
    "Form Definitions": "Definiciones de formulario",

    // ---------------------------------------------------------------------------- Scratchbook
    "Enable/Disable Scratchbook": "Habilitar/Deshabilitar Scratchbook",
    "Show/Hide Scratchbook": "Mostrar/Ocultar Scratchbook",

    // ---------------------------------------------------------------------------- misc. MVC

    // ---------------------------------------------------------------------------- galaxy.pages
    Subscript: false,
    Superscript: false,
    // ---------------------------------------------------------------------------- data
    Trackster: false,
    // ---------------------------------------------------------------------------- dataset-error
    "Any additional comments you can provide regarding what you were doing at the time of the bug.":
        "Cualquier comentario adicional que puedas proporcionar sobre lo que estabas haciendo en el momento que se produjo el error.",
    "Your email address": "Tu dirección de correo electrónico",
    Report: false,
    "Error Report": "Reporte de error",
    // ---------------------------------------------------------------------------- dataset-li
    "Dataset details": "Detalles del conjunto de datos",
    // ---------------------------------------------------------------------------- dataset-edit-attributes
    "Save permissions.": "Guardar permisos",
    "Change the datatype to a new type.": "Cambiar el tipo de datos a uno nuevo",
    "Convert the datatype to a new format.": "Convertir el tipo de datos a un formato nuevo",
    "Save attributes of the dataset.": "Guardar los atributos del conjunto de datos",
    "Change data type": "Cambiar el tipo de datos",
    "Edit dataset attributes": "Editar atributos del conjunto de datos",
    "Save permissions": "Guardar permisos",
    "Manage dataset permissions": "Administrar permisos del conjunto de datos",
    "Change datatype": "Cambiar tipo de datos",
    "Convert datatype": "Convertir tipo de datos",
    "Convert to new format": "Convertir a formato nuevo",
    Save: false,
    Permissions: false,
    Datatypes: false,
    Convert: false,
    Attributes: false,
    // ---------------------------------------------------------------------------- library-dataset-view
    "Import into History": "Importar al historial",
    // ---------------------------------------------------------------------------- library-foldertoolbar-view
    "Location Details": "Detalles de ubicación",
    "Deleting selected items": "Eliminar elementos seleccionados",
    "Please select folders or files": "Por favor, seleccione directorios o archivos",
    "Please enter paths to import": "Por favor, introduce las rutas a importar",
    "Adding datasets from your history": "Agregar conjuntos de datos desde tu historial",
    "Create New Folder": "Crear Nuevo Directorio",
    // ---------------------------------------------------------------------------- library-librarytoolbar-view
    "Create New Library": "Crear Nueva Biblioteca",
    // ---------------------------------------------------------------------------- tours
    Tours: false,
    // ---------------------------------------------------------------------------- user-preferences
    "Click here to sign out of all sessions.": "Haz clic aquí para salir de todas las sesiones",
    "Add or remove custom builds using history datasets.":
        "Agregar o eliminar construcciones personalizadas usando conjuntos de datos del historial",
    "Associate OpenIDs with your account.": "Asociar OpenIDs a su cuenta",
    "Customize your Toolbox by displaying or omitting sets of Tools.":
        "Personalizar Toolbox para mostrar u omitir conjuntos de herramientas",
    "Access your current API key or create a new one.": "Acceder a su clave API actual o crear una nueva",
    "Allows you to change your login credentials.": "Permitir modificar tus credenciales de inicio de sesión ",
    "User Preferences": "Preferencias de usuario",
    "Sign out": "Cerrar sesión",
    "Manage custom builds": "Administrar construcciones personalizadas",
    "Manage OpenIDs": "Administrar OpenIDs",
    "Manage Toolbox filters": "Administrar filtros de Toolbox",
    "Manage API key": "Administrar clave API",
    "Set dataset permissions for new histories": "Establecer permisos de conjuntos de datos para historiales nuevos",
    "Change password": "Cambiar contraseña",
    "Manage information": "Administrar información",
    // ---------------------------------------------------------------------------- shed-list-view
    "Configured Tool Sheds": "Tool Sheds configurados",
    // ---------------------------------------------------------------------------- repository-queue-view
    "Repository Queue": "Cola de repositorio",
    // ---------------------------------------------------------------------------- repo-status-view
    "Repository Status": "Estado del repositorio",
    // ---------------------------------------------------------------------------- workflows-view
    "Workflows Missing Tools": "Flujos de trabajo a los que les faltan herramientas",
    // ---------------------------------------------------------------------------- tool-form-base
    "See in Tool Shed": "Ver en Tool Shed",
    Requirements: false,
    Share: false,
    // ---------------------------------------------------------------------------- tool-form-composite
    "Workflow submission failed": "Error en el envío de flujo de trabajo",
    "Run workflow": "Ejecutar flujo de trabajo",
    // ---------------------------------------------------------------------------- tool-form
    "Job submission failed": "Error en envío de trabajo",
    Execute: false,
    "Tool request failed": "Error en solicitud de herramienta",
    // ---------------------------------------------------------------------------- workflow
    // ---------------------------------------------------------------------------- workflow-view
    "Copy and insert individual steps": "Copiar e insertar pasos individuales",
    Warning: false,
    // ---------------------------------------------------------------------------- workflow-forms
    "An email notification will be sent when the job has completed.":
        "Se enviará una notificación por correo electrónico cuando el trabajo haya sido completado",
    "Add a step label.": "Agregar una etiqueta de paso",
    "Assign columns": "Asignar columnas",
    // ---------------------------------------------------------------------------- form-repeat
    "Delete this repeat block": "Borrar este bloque repetido",
    placeholder: false,
    Repeat: false,
    // ---------------------------------------------------------------------------- ui-frames
    Error: false,
    Close: false,
    // ---------------------------------------------------------------------------- upload-view
    "Download from web or upload from disk": "Descargar de la red o cargar desde disco",
    Collection: false,
    Composite: false,
    Regular: false,
    // ---------------------------------------------------------------------------- default-row
    "Upload configuration": "Cargar configuración",
    // ---------------------------------------------------------------------------- default-view
    "FTP files": "Archivos FTP",
    Reset: false,
    Pause: false,
    Start: false,
    "Choose FTP file": "Elegir archivo FTP",
    "Choose local file": "Elegir archivo local",
    // ---------------------------------------------------------------------------- collection-view
    Build: false,
    "Choose FTP files": "Elegir archivos FTP",
    "Choose local files": "Elegir archivos locales",
    // ---------------------------------------------------------------------------- composite-row
    Select: false,
    // ---------------------------------------------------------------------------- list-of-pairs-collection-creator
    "Create a collection of paired datasets": "Crear una colección de conjuntos de datos pareados",
    // ---------------------------------------------------------------------------- history-panel
    "View all histories": "Ver todos los historiales",
    "History options": "Opciones de historial",
    "Refresh history": "Actualizar historial",
    // ---------------------------------------------------------------------------- admin-panel
    "View error logs": "Ver registros de error",
    "View migration stages": "Ver etapas de migración",
    "View lineage": "Ver linaje",
    "Manage dependencies": "Administrar dependencias",
    "Manage allowlist": "Administrar lista de permitidos",
    "Manage metadata": "Administrar metadatos",
    "Manage tools": "Administrar herramientas",
    "Monitor installation": "Monitorear instalación",
    "Install new tools": "Instalar nuevas herramientas",
    "Tool Management": "Gestión de herramienta",
    Forms: false,
    "User Management": "Gestión de usuario",
    "Manage jobs": "Administrar trabajos",
    "Display applications": "Mostrar aplicaciones",
    "Data tables": "Tablas de datos",
    "Data types": "Tipos de datos",
    Server: false,
    // ---------------------------------------------------------------------------- circster
    "Could Not Save": "No se pudo guardar",
    "Saving...": "Guardando",
    Settings: false,
    "Add tracks": "Agregar pistas",
    // ---------------------------------------------------------------------------- trackster
    "New Visualization": "Nueva visualización",
    "Add Data to Saved Visualization": "Agregar datos a visualización guardada",
    "Close visualization": "Cerrar visualización",
    Circster: false,
    Bookmarks: false,
    "Add group": "Agregar grupo",
    // ---------------------------------------------------------------------------- sweepster
    "Remove parameter from tree": "Eliminar parámetro del árbol",
    "Add parameter to tree": "Agregar parámetro al árbol",
    Remove: false,
    // ---------------------------------------------------------------------------- visualization
    "Select datasets for new tracks": "Seleccionar conjuntos de datos para nuevas pistas",
    Libraries: false,
    // ---------------------------------------------------------------------------- phyloviz
    "Zoom out": "Alejar",
    "Zoom in": "Acercar",
    "Phyloviz Help": "Ayuda de PhyloViz",
    "Save visualization": "Guardar visualización",
    "PhyloViz Settings": "Ajustes de PhyloViz",
    Title: false,
    // ---------------------------------------------------------------------------- filters
    "Filtering Dataset": "Filtrando conjunto de datos",
    "Filter Dataset": "Filtrar conjunto de datos",
    // ---------------------------------------------------------------------------- tracks
    "Show individual tracks": "Mostrar pistas individuales",
    "Trackster Error": "Error de Trackster",
    "Tool parameter space visualization": "Visualización del espacio de parámetros de la herramienta",
    Tool: false,
    "Set as overview": "Establecer como descripción general",
    "Set display mode": "Establecer modo de visualización",
    Filters: false,
    "Show composite track": "Mostrar pista compuesta",
    "Edit settings": "Editar configuración",
    // ---------------------------------------------------------------------------- modal_tests
    "Test title": false,
    // ---------------------------------------------------------------------------- popover_tests
    "Test Title": "Título de prueba",
    "Test button": "Botón de prueba",
    // ---------------------------------------------------------------------------- ui_tests
    title: false,
    // ---------------------------------------------------------------------------- user-custom-builds
    "Create new Build": "Crear nueva construcción",
    "Delete custom build.": "Eliminar construcción personalizada",
    "Provide the data source.": "Proporcionar la fuente de datos",
    // ---------------------------------------------------------------------------- scratchbook
    "Next in History": "Siguiente en historial",
    "Previous in History": "Anterior en historial",
    // ---------------------------------------------------------------------------- generic-nav-view
    "Chat online": "Conversar en línea",
    // ---------------------------------------------------------------------------- ui-select-content
    "Multiple collections": "Varias colecciones",
    "Dataset collections": "Colecciones de conjuntos de datos",
    "Dataset collection": "Colección de conjunto de datos",
    "Multiple datasets": "Varios conjuntos de datos",
    "Single dataset": "Conjunto de datos único",
    // ---------------------------------------------------------------------------- upload-button
    "Download from URL or upload files from disk": "Descargar desde URL o descargar desde disco",
    // ---------------------------------------------------------------------------- workflow_editor_tests
    "tool tooltip": "Mensaje de información sobre herramientas",
    // ----------------------------------------------------------------------------
});
