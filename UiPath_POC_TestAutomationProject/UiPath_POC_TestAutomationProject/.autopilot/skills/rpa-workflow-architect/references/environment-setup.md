# Phase 0: Environment Readiness

**Goal:** Ensure Studio Desktop has a project open and the project context is accessible before any other operations.

## Step 0.1: Establish Project Root

The tools operate within the context of the currently open Studio Desktop project. Use `GetProjectContextTool` to confirm the project is available and to identify the project root.

```
GetProjectContextTool:
  queryType: "full"
```

This returns the project root path, installed packages, expression language, connections, and other project-level context. If the tool fails or returns no project data, ask the user to open their project in Studio Desktop first.

Store the project root path and use it consistently as `{projectRoot}` throughout all subsequent operations.

## Step 0.2: Verify Project Is Open

If `GetProjectContextTool` returns no project data or fails, the project may not be open in Studio Desktop:

1. Ask the user to open their UiPath project in Studio Desktop
2. Once opened, retry `GetProjectContextTool` to confirm context is available

**Note:** Unlike CLI-based workflows, there is no need to manually start Studio or open a project programmatically — these actions require the user to interact directly with Studio Desktop.

## Step 0.3: Authentication

Authentication is handled automatically by Studio Desktop. If an Integration Service connection fails (e.g., during dynamic activity resolution), inform the user to re-authenticate the connection via Studio Desktop's Integration Service panel.

## Step 0.4: Creating a New Project

When the user needs a brand-new UiPath project (not just a new workflow in an existing project), guide them to:

1. Open Studio Desktop
2. Go to **File > New > Process** (or appropriate template: Library, Test Automation)
3. Set the project name, location, expression language (VB.NET or C#), and target framework (Windows recommended)
4. Click **Create**

Once the project is created and open in Studio Desktop, proceed to Phase 1 (Discovery) using the project context returned by `GetProjectContextTool`.

### Project Settings to Confirm With User

| Setting | Options | Notes |
|---------|---------|-------|
| Expression Language | `VisualBasic`, `CSharp` | Determines XAML expression syntax throughout the project |
| Target Framework | `Windows`, `Portable`, `Legacy` | Windows is recommended for most automation scenarios |
| Project Template | Process, Library, Test Automation | Choose based on use case |
