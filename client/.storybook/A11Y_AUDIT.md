# Initial accessibility audit

2026-10-10, forked from `vitest_story_play` at `19b6b1a85542397c258748f6b075f4d25f4c8053`.
Storybook 10.6.1, axe-core 4.14.0, Playwright Chromium, default Vitest viewport,
WCAG 2.0/2.1 A and AA, best practices, and WCAG 2.2 AA.

The initial strict run had 236 stories: 115 passed, 120 failed axe, and one
collection-refresh play failed before its audit. These are story-level results,
not 120 distinct component defects or a full accessibility assessment.
Shared controls account for many repeated findings. A rerun reached the refresh story's audit and found four axe rules too, bringing
the observed exceptions to 121; the other 115 stories retain strict checks.

Each observed axe failure has a story-level `todo`; new stories inherit `error`.
No rules or application elements are excluded to obtain a green run. A `todo`
keeps findings visible in Storybook but emits no CLI/CI accessibility diagnostics.
Stories spreading another story also inherit its parameters; explicitly reset
`a11y.test` to `error` when making a clean state from an excepted story.

| Story file                                                                                                                                                      | Excepted stories | Observed rules                                                                         |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------: | -------------------------------------------------------------------------------------- |
| [src/components/Collections/ListCollectionCreator.stories.ts](../src/components/Collections/ListCollectionCreator.stories.ts)                                   |                5 | `aria-allowed-role`, `color-contrast`, `nested-interactive`, `target-size`             |
| [src/components/Collections/PairCollectionCreator.stories.ts](../src/components/Collections/PairCollectionCreator.stories.ts)                                   |                3 | `aria-allowed-role`, `nested-interactive`                                              |
| [src/components/CommandPalette/CommandPalette.stories.ts](../src/components/CommandPalette/CommandPalette.stories.ts)                                           |               14 | `aria-required-children`                                                               |
| [src/components/Common/ExportForm.stories.ts](../src/components/Common/ExportForm.stories.ts)                                                                   |                4 | `label-title-only`                                                                     |
| [src/components/FilesDialog/FilesDialog.stories.ts](../src/components/FilesDialog/FilesDialog.stories.ts)                                                       |               14 | `button-name`, `nested-interactive`, `target-size`                                     |
| [src/components/Form/Elements/FormData/FormData.stories.ts](../src/components/Form/Elements/FormData/FormData.stories.ts)                                       |                5 | `tabindex`, `target-size`                                                              |
| [src/components/Form/Elements/FormOptionalText.stories.ts](../src/components/Form/Elements/FormOptionalText.stories.ts)                                         |                2 | `label`                                                                                |
| [src/components/Form/Elements/FormSelection.stories.ts](../src/components/Form/Elements/FormSelection.stories.ts)                                               |                7 | `aria-required-attr`, `tabindex`, `target-size`                                        |
| [src/components/History/Export/HistoryExportWizard.stories.ts](../src/components/History/Export/HistoryExportWizard.stories.ts)                                 |                4 | `button-name`, `label-title-only`, `link-in-text-block`                                |
| [src/components/Libraries/LibraryPermissions/PermissionsInputField.stories.ts](../src/components/Libraries/LibraryPermissions/PermissionsInputField.stories.ts) |                2 | `color-contrast`, `tabindex`                                                           |
| [src/components/Login/ChangePassword.stories.ts](../src/components/Login/ChangePassword.stories.ts)                                                             |                3 | `label`                                                                                |
| [src/components/ObjectStore/ConfigurationMarkdown.stories.ts](../src/components/ObjectStore/ConfigurationMarkdown.stories.ts)                                   |                1 | `link-in-text-block`                                                                   |
| [src/components/ObjectStore/ObjectStoreBadges.stories.ts](../src/components/ObjectStore/ObjectStoreBadges.stories.ts)                                           |                2 | `aria-prohibited-attr`                                                                 |
| [src/components/ScrollList/ScrollList.stories.ts](../src/components/ScrollList/ScrollList.stories.ts)                                                           |                7 | `aria-required-children`, `button-name`, `scrollable-region-focusable`                 |
| [src/components/SelectionField/SelectionField.stories.ts](../src/components/SelectionField/SelectionField.stories.ts)                                           |                2 | `aria-required-attr`                                                                   |
| [src/components/Tool/ToolCard.stories.ts](../src/components/Tool/ToolCard.stories.ts)                                                                           |                6 | `label-content-name-mismatch`, `nested-interactive`                                    |
| [src/components/Toolshed/RepositoryDetails/InstallationSettings.stories.ts](../src/components/Toolshed/RepositoryDetails/InstallationSettings.stories.ts)       |                5 | `button-name`, `label`                                                                 |
| [src/components/User/DiskUsage/Quota/QuotaUsageSummary.stories.ts](../src/components/User/DiskUsage/Quota/QuotaUsageSummary.stories.ts)                         |                2 | `aria-progressbar-name`                                                                |
| [src/components/User/UserDeletion.stories.ts](../src/components/User/UserDeletion.stories.ts)                                                                   |                2 | `button-name`                                                                          |
| [src/components/Workflow/Run/WorkflowMissingToolsRequest.stories.ts](../src/components/Workflow/Run/WorkflowMissingToolsRequest.stories.ts)                     |                5 | `button-name`                                                                          |
| [src/components/Workflow/WorkflowAnnotation.stories.ts](../src/components/Workflow/WorkflowAnnotation.stories.ts)                                               |                2 | `label-content-name-mismatch`                                                          |
| [src/components/WorkflowInvocationState/WorkflowInvocationOverview.stories.ts](../src/components/WorkflowInvocationState/WorkflowInvocationOverview.stories.ts) |                1 | `label-content-name-mismatch`                                                          |
| [src/components/WorkflowInvocationState/WorkflowInvocationShare.stories.ts](../src/components/WorkflowInvocationState/WorkflowInvocationShare.stories.ts)       |                1 | `button-name`                                                                          |
| [src/components/WorkflowInvocationState/WorkflowInvocationState.stories.ts](../src/components/WorkflowInvocationState/WorkflowInvocationState.stories.ts)       |                6 | `aria-progressbar-name`, `aria-prohibited-attr`, `label-content-name-mismatch`, `list` |
| [src/components/admin/QuotaForm.stories.ts](../src/components/admin/QuotaForm.stories.ts)                                                                       |                8 | `color-contrast`, `label`, `tabindex`                                                  |
| [src/components/admin/RoleForm.stories.ts](../src/components/admin/RoleForm.stories.ts)                                                                         |                8 | `aria-required-attr`, `color-contrast`, `label`, `tabindex`                            |

## Stories to revisit

### src/components/Collections/ListCollectionCreator.stories.ts

- `KeepsListOnRefresh`: `aria-allowed-role`, `color-contrast`, `nested-interactive`, `target-size`
- `TwoDatasetsInHistory`: `color-contrast`
- `DropsDeletedDataset`: `aria-allowed-role`, `color-contrast`, `nested-interactive`, `target-size`
- `DropsFailedDataset`: `aria-allowed-role`, `color-contrast`, `nested-interactive`, `target-size`
- `FailedDatasetInHistory`: `color-contrast`

### src/components/Collections/PairCollectionCreator.stories.ts

- `KeepsPairOnRefresh`: `aria-allowed-role`, `nested-interactive`
- `DropsDeletedDataset`: `aria-allowed-role`, `nested-interactive`
- `DropsFailedDataset`: `aria-allowed-role`, `nested-interactive`

### src/components/CommandPalette/CommandPalette.stories.ts

- `OffersCategoriesWhileSearching`: `aria-required-children`
- `TurnsScopeIntoBadge`: `aria-required-children`
- `RemovesBadgeByClick`: `aria-required-children`
- `KeepsBadgeWhileEditing`: `aria-required-children`
- `ExplainsShortcuts`: `aria-required-children`
- `AppliesScopeFromHelp`: `aria-required-children`
- `PicksUploadMethodByClick`: `aria-required-children`
- `OpensWorkflowPicker`: `aria-required-children`
- `PromptsForHistoryName`: `aria-required-children`
- `KeepsAskingForReportTitle`: `aria-required-children`
- `ResetsCategoryOnClear`: `aria-required-children`
- `SearchesScopeWithNoResults`: `aria-required-children`
- `ReportsScopeLoadFailure`: `aria-required-children`
- `SearchesScopeFromScratch`: `aria-required-children`

### src/components/Common/ExportForm.stories.ts

- `HistoryArchive`: `label-title-only`
- `History`: `label-title-only`
- `ExportsNamedFile`: `label-title-only`
- `ClearsAfterExport`: `label-title-only`

### src/components/FilesDialog/FilesDialog.stories.ts

- `MultipleFiles`: `button-name`, `nested-interactive`, `target-size`
- `SelectsFiles`: `button-name`, `nested-interactive`, `target-size`
- `SelectsDirectoryContents`: `button-name`, `nested-interactive`, `target-size`
- `UnselectsSubdirectory`: `button-name`, `nested-interactive`, `target-size`
- `SelectsAll`: `button-name`, `nested-interactive`, `target-size`
- `ShowsFtpHelp`: `button-name`, `nested-interactive`, `target-size`
- `RecoversFromSourceError`: `button-name`, `nested-interactive`, `target-size`
- `MultipleFilesWithTemplates`: `button-name`, `nested-interactive`, `target-size`
- `SingleFileWithTemplates`: `button-name`, `nested-interactive`, `target-size`
- `CreatesSourcesFromRootOnly`: `button-name`, `nested-interactive`, `target-size`
- `Directories`: `button-name`, `nested-interactive`, `target-size`
- `ListsDirectoriesOnly`: `button-name`, `nested-interactive`, `target-size`
- `SelectsFolderByOpening`: `button-name`, `nested-interactive`, `target-size`
- `DirectoriesRecoverFromSourceError`: `button-name`, `nested-interactive`, `target-size`

### src/components/Form/Elements/FormData/FormData.stories.ts

- `MultipleDatasets`: `tabindex`, `target-size`
- `MultipleDatasetsSelectedOutOfOrder`: `tabindex`, `target-size`
- `MultipleDatasetsAndElementsIntermixed`: `tabindex`, `target-size`
- `TwoCollectionElementsThatAreDatasets`: `tabindex`, `target-size`
- `CollectionOnMultipleDatasetsInput`: `tabindex`, `target-size`

### src/components/Form/Elements/FormOptionalText.stories.ts

- `WithValue`: `label`
- `SwitchesOffAndBackOn`: `label`

### src/components/Form/Elements/FormSelection.stories.ts

- `MultipleRequired`: `tabindex`, `target-size`
- `MultipleOptional`: `tabindex`, `target-size`
- `ListsOptionsInOrder`: `aria-required-attr`
- `OffersNothingSelected`: `aria-required-attr`
- `ClearsByPickingNothing`: `aria-required-attr`
- `ClearsRequiredMultiple`: `aria-required-attr`
- `TogglesMultipleOptions`: `aria-required-attr`, `tabindex`

### src/components/History/Export/HistoryExportWizard.stories.ts

- `ExportsDirectDownload`: `button-name`
- `SuggestsRemoteFileName`: `button-name`, `label-title-only`
- `SetsUpZenodoDraftRecord`: `button-name`
- `PrefersUserZenodo`: `button-name`, `link-in-text-block`

### src/components/Libraries/LibraryPermissions/PermissionsInputField.stories.ts

- `NoRolesChosen`: `color-contrast`
- `RolesChosen`: `tabindex`

### src/components/Login/ChangePassword.stories.ts

- `ResetFromEmailLink`: `label`
- `PasswordExpired`: `label`
- `ResetLinkExpired`: `label`

### src/components/ObjectStore/ConfigurationMarkdown.stories.ts

- `AdminConfigured`: `link-in-text-block`

### src/components/ObjectStore/ObjectStoreBadges.stories.ts

- `DefaultSize`: `aria-prohibited-attr`
- `DoubleSize`: `aria-prohibited-attr`

### src/components/ScrollList/ScrollList.stories.ts

- `PagedFromLoader`: `aria-required-children`, `button-name`
- `CountInFooter`: `button-name`
- `GivenItems`: `aria-required-children`, `button-name`, `scrollable-region-focusable`
- `StoreOwnedItems`: `button-name`
- `LoadsEveryPageOnScroll`: `aria-required-children`, `scrollable-region-focusable`
- `CountsEveryPageOnceLoaded`: `aria-required-children`, `scrollable-region-focusable`
- `CountsItemAddedOutsideLoader`: `aria-required-children`, `button-name`, `scrollable-region-focusable`

### src/components/SelectionField/SelectionField.stories.ts

- `ListsHistoryDatasets`: `aria-required-attr`
- `ListsWorkflowLabels`: `aria-required-attr`

### src/components/Tool/ToolCard.stories.ts

- `LatestVersion`: `nested-interactive`
- `OffersAdminToolOptions`: `nested-interactive`
- `OffersUserToolOptions`: `nested-interactive`
- `NewerVersionAvailable`: `label-content-name-mismatch`, `nested-interactive`
- `SingleVersion`: `nested-interactive`
- `WithRunButton`: `nested-interactive`

### src/components/Toolshed/RepositoryDetails/InstallationSettings.stories.ts

- `WithToolPanel`: `button-name`, `label`
- `WithoutToolPanel`: `button-name`
- `SeveralToolConfigs`: `button-name`, `label`
- `ChecksEnabledDependencies`: `button-name`, `label`
- `UnchecksDisabledDependencies`: `button-name`, `label`

### src/components/User/DiskUsage/Quota/QuotaUsageSummary.stories.ts

- `MixedQuotas`: `aria-progressbar-name`
- `AllUnlimited`: `aria-progressbar-name`

### src/components/User/UserDeletion.stories.ts

- `AwaitingConfirmation`: `button-name`
- `SelfDeletionNotAllowed`: `button-name`

### src/components/Workflow/Run/WorkflowMissingToolsRequest.stories.ts

- `AsksForOneTool`: `button-name`
- `NotesTruncatedRequest`: `button-name`
- `CancelsAndReopens`: `button-name`
- `ShowsErrorInDialog`: `button-name`
- `ClearsErrorOnCancel`: `button-name`

### src/components/Workflow/WorkflowAnnotation.stories.ts

- `RunForm`: `label-content-name-mismatch`
- `Invocation`: `label-content-name-mismatch`

### src/components/WorkflowInvocationState/WorkflowInvocationOverview.stories.ts

- `WorkflowGraph`: `label-content-name-mismatch`

### src/components/WorkflowInvocationState/WorkflowInvocationShare.stories.ts

- `AsksBeforeSharing`: `button-name`

### src/components/WorkflowInvocationState/WorkflowInvocationState.stories.ts

- `Completed`: `aria-progressbar-name`, `label-content-name-mismatch`, `list`
- `SchedulingNew`: `aria-progressbar-name`, `aria-prohibited-attr`, `label-content-name-mismatch`, `list`
- `JobRunning`: `aria-progressbar-name`, `aria-prohibited-attr`, `label-content-name-mismatch`, `list`
- `JobsBeingCreated`: `aria-progressbar-name`, `aria-prohibited-attr`, `label-content-name-mismatch`, `list`
- `JobFailedWhileAnotherRuns`: `aria-progressbar-name`, `aria-prohibited-attr`, `label-content-name-mismatch`, `list`
- `JobFailed`: `aria-progressbar-name`, `label-content-name-mismatch`, `list`

### src/components/admin/QuotaForm.stories.ts

- `NewQuota`: `color-contrast`, `label`
- `RequiresDescription`: `color-contrast`, `label`
- `NewQuotaForLabeledStorage`: `color-contrast`, `label`
- `ExistingQuota`: `label`, `tabindex`
- `KeepsSavedNameWhileRenaming`: `label`, `tabindex`
- `MakesQuotaADefault`: `label`
- `RequiresNameAndAmount`: `label`, `tabindex`
- `ExistingDefaultQuota`: `label`

### src/components/admin/RoleForm.stories.ts

- `NewRole`: `color-contrast`, `label`
- `WaitsForGroups`: `color-contrast`, `label`
- `RequiresNameAndDescription`: `color-contrast`, `label`
- `SearchesUsersByEmail`: `aria-required-attr`, `color-contrast`, `label`
- `NewRoleNameTaken`: `color-contrast`, `label`
- `ExistingRole`: `label`, `tabindex`
- `KeepsSavedNameWhileRenaming`: `label`, `tabindex`
- `ExistingRoleNameTaken`: `label`, `tabindex`
