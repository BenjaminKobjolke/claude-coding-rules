# Version
2

Increase this version number whenever this rule file changes.

# C# Rules (.NET)

See `COMMON_RULES.md` for rules that apply to all languages.

## Optional rule files

- `csharp/WINFORMS.md` — Windows Forms desktop app (localization, tray icon, app structure,
  settings, Costura, startup, dark theme). Run `/coding-rules:apply` to add it when the project
  gains a Windows Forms UI.

## Async/Await

Use `async`/`await` for all I/O operations (file access, network, database). Never block on
async code with `.Result` or `.Wait()` — this risks deadlocks, especially in UI and ASP.NET
contexts. Propagate `async` all the way up the call chain.

---

## Exception Hierarchy

Create custom exception types for domain errors instead of throwing generic `Exception`. Catch
specific exception types — avoid bare `catch (Exception)` unless it is a top-level handler.

---

## Logging

Route all logging through one class named **`AppLogger`** (`AppLogger.cs`) that wraps the
underlying sink (`Microsoft.Extensions.Logging`, Serilog, etc.). Feature code calls `AppLogger`,
never `Console.WriteLine`/`Debug.WriteLine` or a raw `ILogger` directly — this gives a single
enable/level toggle without touching call sites.

```csharp
AppLogger.Info("User loaded: {0}", userId);
AppLogger.Error(ex, "Failed to load user {0}", userId);
```

---

## Dependency Injection

Use `Microsoft.Extensions.DependencyInjection` or a similar IoC container to manage service
lifetimes and dependencies. Register services at startup and inject them via constructors.

---

## Disposal

Managers that hold unmanaged or disposable resources implement `IDisposable`. Owners dispose
those managers, and callers prefer `using` when a resource has a clear scope.

```csharp
using (var stream = File.OpenRead(path))
{
    Process(stream);
}
```

## Required Batch Files

Every project must include these batch files in the `tools/` directory:

- `tools/run_tests.bat` - Runs the test suite
- `tools/build_release.bat` - Builds the release version

---

## Self-Describing Classes

Implement the common "Self-Describing Classes" rule using interfaces or custom attributes.

### Option A: Interface with explicit method

```csharp
public interface ISearchable
{
    IReadOnlyList<string> GetSearchableFields();
}

public class Customer : ISearchable
{
    public string Name { get; set; }
    public string Email { get; set; }
    public string Phone { get; set; }

    public IReadOnlyList<string> GetSearchableFields()
    {
        return new[] { Name, Email, Phone };
    }
}
```

### Option B: Custom attribute on properties

```csharp
[AttributeUsage(AttributeTargets.Property)]
public class SearchableAttribute : Attribute { }

public class Customer
{
    [Searchable] public string Name { get; set; }
    [Searchable] public string Email { get; set; }
    public string InternalNotes { get; set; } // not searchable
}

// Consumer uses reflection once at startup:
// typeof(Customer).GetProperties()
//     .Where(p => p.GetCustomAttribute<SearchableAttribute>() != null)
```

Prefer the interface approach when the logic is non-trivial. Use attributes when you want
declarative opt-in per property and can tolerate the reflection cost.
