# Validation & Fixing (Phase 3 Details)

Detailed procedures for package resolution, dynamic types, debugging, iteration, and smoke testing.

## Package Error Resolution

```
# Install latest stable version (omit version to default to latest)
InstallOrUpdatePackagesTool:
  packages: [{"id": "UiPath.Excel.Activities"}]

# Install a specific version when needed
InstallOrUpdatePackagesTool:
  packages: [{"id": "UiPath.Excel.Activities", "version": "x.y.z"}]
```

**Only `id` is required** by `InstallOrUpdatePackagesTool` — omitting `version` installs the latest compatible version. Prefer omitting the version unless you have a specific compatibility reason to pin an older one.

Use `GetPackageVersionsTool` if you need to inspect available versions before deciding:
```
GetPackageVersionsTool:
  packageId: "UiPath.Excel.Activities"
  includePrerelease: false
```

**If `InstallOrUpdatePackagesTool` fails:**
- **Package not found**: Verify the exact package ID — check spelling, use `RpaActivitySearchTool` to discover the correct package name from an activity's description
- **Network/feed error**: The user may need to check their NuGet feed configuration in Studio settings

## Resolving Dynamic Activity Custom Types

Dynamic activities (e.g., Integration Service connectors) retrieved via `RpaActivityDefaultTool` (with `isDynamicActivity: true`) may use **JIT-compiled custom types** for their input/output properties. After the activity is added to the workflow, when you need to discover the property names and CLR types of these custom entities (e.g., to populate an `Assign` activity targeting a custom type property, or to create a variable of a custom type), read the JIT custom types schema:

```
ReadFileTool:
  filePath: {projectRoot}/.project/JitCustomTypesSchema.json
```

## Focus Activity for Debugging

When `GetErrorsTool` returns an error referencing a specific activity (by IdRef or DisplayName), use `FocusActivityTool` to highlight it in the Studio designer. This helps the user see the problematic activity in context and verify fixes visually:

```
# Focus a specific activity by its IdRef (from the error output):
FocusActivityTool:
  activityId: "Assign_1"

# Focus all activities sequentially (useful for walkthrough):
FocusActivityTool
```

This is especially useful when:
- An error references an activity and you want the user to confirm the context
- You've made a fix and want to show the user which activity was modified
- The error is ambiguous and you need to verify which activity instance is affected

## Iteration Loop

```
REPEAT:
  1. GetErrorsTool → onlyCurrentFile: true, revalidate: true
  2. IF 0 errors (or errors cannot be resolved automatically) → EXIT to Phase 4
  3. Identify highest-priority error category
  4. Apply appropriate fix
  5. (Optional) Focus the fixed activity: FocusActivityTool → activityId: "..."
  6. GOTO 1

DO NOT stop until all activities are resolved (recognized).
DO NOT obsess on one error. If it can't be resolved, skip it, continue, and defer to a user action through an informative, step-by-step message at the end.
DO NOT skip validation steps.
DO NOT assume edits worked without checking.
```

Expect multiple iteration cycles for complex workflows.

## Smoke Test (Optional but Recommended)

**Important:** `GetErrorsTool` (Studio validation) and `RunWorkflowTool` (runtime compilation) use different validation paths. Some errors — such as invalid enum values on activity properties — pass Studio validation but fail at runtime. Always treat the smoke test as a critical validation step, not just an optional extra.

After reaching 0 errors, optionally run the workflow to catch runtime errors (wrong credentials, missing files, logic bugs) that static validation cannot detect:

```
# Run with default arguments:
RunWorkflowTool:
  filePath: {projectRoot}/Workflows/MyWorkflow.xaml   # full absolute path required

# Run with input arguments:
RunWorkflowTool:
  filePath: {projectRoot}/Workflows/MyWorkflow.xaml
  inputArgumentsJson: '{"recipientEmail": "test@example.com", "subject": "Test"}'
```

**When to run:**
- The workflow has no compilation errors but you want to verify runtime behavior
- The workflow involves file I/O, API calls, or data transformations that could fail at runtime
- The user specifically asks to test the workflow

**When NOT to run:**
- The workflow has side effects (sends emails, modifies databases, calls external APIs) — warn the user first
- The workflow requires interactive input (UI automation, attended triggers)
- Compilation errors still exist (fix those first)

If `RunWorkflowTool` reveals runtime errors, analyze the output and loop back to fix them.

## Diagnosing Runtime Failures

When a run fails and the error output doesn't immediately pinpoint the cause, narrow it down with the run-only tool:

- **Re-run with representative input arguments** (`inputArgumentsJson`) so the failing path is actually exercised.
- **Read the error output carefully** — it carries the compilation or runtime error (e.g. a parse exception, a null reference, an invalid property value).
- **Isolate by scope** — for a large workflow, temporarily run a smaller workflow (or remove downstream activities) to confirm where the data first goes wrong, then fix and re-run.
- **Loop** — fix the most likely cause, re-run, and repeat until the run succeeds.

See **[running-workflows.md](running-workflows.md)** for the full `RunWorkflowTool` parameter reference and input-argument format.
