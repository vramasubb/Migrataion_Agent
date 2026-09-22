# Running Workflows with `RunWorkflowTool`

`RunWorkflowTool` runs a workflow file once and reports the result. It is the runtime "smoke test" that complements `GetErrorsTool` (static validation): static checks catch structural and type issues at design time, while running the workflow catches problems that only surface at execution — wrong credentials, missing files, bad API responses, null references, and logic errors.

> This tool performs a single end-to-end run. It does not support breakpoints, stepping, or interactive debug sessions — use it to execute the workflow and read back its output or error.

---

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `filePath` | Yes | Full absolute path of the workflow file to run (e.g. `{projectRoot}/Workflows/MyWorkflow.xaml`). |
| `inputArgumentsJson` | No | Project-level input arguments as a JSON **object string** mapping each argument name to its value. Omit (or pass an empty string) when the workflow has no input arguments. |

```
RunWorkflowTool:
  filePath: {projectRoot}/Workflows/MyWorkflow.xaml
  inputArgumentsJson: '{"recipientEmail": "test@example.com", "subject": "Test"}'
```

---

## Input Arguments

Input arguments are the workflow's **project-level In/InOut parameters** — its public interface for passing data in. Provide them through `inputArgumentsJson` as a single JSON object string:

- Keys are argument names; values are plain JSON values (string, number, boolean, or null).
- Use **double quotes** for keys and string values — `{"firstName": "Ada", "count": 3, "enabled": true}`.
- **Single-quoted JSON is invalid and is rejected** (e.g. `{'firstName': 'Ada'}` fails).
- Omit the field (or pass `''`) to run with no input arguments.

```
# Run with no input arguments
RunWorkflowTool:
  filePath: {projectRoot}/Workflows/Hello.xaml

# Run with input arguments
RunWorkflowTool:
  filePath: {projectRoot}/Workflows/ProcessOrder.xaml
  inputArgumentsJson: '{"orderId": "ORD-12345", "customerEmail": "test@example.com"}'
```

---

## Reading the Result

The tool returns a single text result:

- **Success** — `Workflow <filePath> ran successfully with the following output: <output>`. The workflow compiled and executed without runtime errors.
- **Failure** — `Failed to run workflow <filePath>: <error>`. The error text carries the compilation or runtime failure.

When a run fails, read the error, form a hypothesis about the root cause, fix the workflow (`RpaWorkflowEditTool`), and run again. Common runtime failures and where to look:

| Symptom in the error | Likely cause | Fix |
|----------------------|--------------|-----|
| `JsonReaderException` / parse error | The activity received a non-JSON response (e.g. an HTTP 429/500 page) | Check the status code before deserializing; add retry/backoff |
| Null reference | An upstream activity didn't populate a variable | Verify the producing activity ran and assigned the value |
| Invalid enum / property value | A value that passed static validation but fails at runtime | Correct the property to a supported value |
| Wrong credentials / missing file | Environment or configuration issue | Surface to the user with what needs to be provided |

---

## When to Run

**Run when:**
- The workflow has 0 static errors and you want to confirm runtime behavior.
- It involves file I/O, API calls, or data transformations that can fail at runtime.
- The user asks to test the workflow.

**Do NOT run when:**
- The workflow has side effects (sends email, modifies data, calls external APIs) — warn the user first.
- It requires interactive input (UI automation, attended triggers).
- Compilation errors still exist — fix those first with `GetErrorsTool`.
