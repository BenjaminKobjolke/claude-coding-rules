# Version
1

Increase this version number whenever this rule file changes.

# C# Rules (.NET Framework / Windows Forms)

See `COMMON_RULES.md` for rules that apply to all languages.

## Localization

Use the `csharp-localization` library for multi-language support:
https://github.com/BenjaminKobjolke/csharp-localization

Clone it next to your solution so the project reference below resolves.

### Installation

Add as a project reference in your `.csproj`:

```xml
<ProjectReference Include="..\csharp-localization\src\CSharpLocalization\CSharpLocalization.csproj">
  <Project>{8A7B5F1E-3D2C-4E6F-9A1B-5C8D7E2F4A3B}</Project>
  <Name>CSharpLocalization</Name>
</ProjectReference>
```

### Directory Structure

```
project/
├── lang/
│   ├── en.json         # English (default)
│   ├── de.json         # German
│   ├── languages.json  # Language metadata
│   └── ...
├── Properties/
└── Program.cs
```

### Translation File Format

Create `lang/en.json`:

```json
{
  "app": {
    "title": "My Application"
  },
  "nav": {
    "dashboard": "Dashboard",
    "settings": "Settings"
  },
  "tray": {
    "show": "Show",
    "exit": "Exit"
  },
  "common": {
    "cancel": "Cancel",
    "save": "Save"
  }
}
```

### Setup with Embedded Resources

Add language files as embedded resources in `.csproj`:

```xml
<ItemGroup>
  <EmbeddedResource Include="lang\en.json">
    <LogicalName>MyApp.lang.en.json</LogicalName>
  </EmbeddedResource>
  <EmbeddedResource Include="lang\de.json">
    <LogicalName>MyApp.lang.de.json</LogicalName>
  </EmbeddedResource>
  <EmbeddedResource Include="lang\languages.json">
    <LogicalName>MyApp.lang.languages.json</LogicalName>
  </EmbeddedResource>
</ItemGroup>
```

### Initialization

```csharp
using System.Reflection;
using CSharpLocalization;

private Localization _localization;

private void InitializeLocalization()
{
    _localization = new Localization(new LocalizationConfig
    {
        UseEmbeddedResources = true,
        ResourceAssembly = Assembly.GetExecutingAssembly(),
        ResourcePrefix = "MyApp.lang.",
        DefaultLang = null,  // null = auto-detect from system
        FallbackLang = "en"
    });
}
```

### Usage

```csharp
// Simple translation
string title = _localization.Lang("app.title");

// With placeholders
string message = _localization.Lang("messages.welcome", new Dictionary<string, string>
{
    { ":name", userName }
});

// Change language
_localization.SetLanguage("de");
```

---

## Tray Icon Setup (Theme-Aware)

Windows Forms applications with system tray icons should support both light and dark Windows themes.

### Icon Files

Example icons can be found in the `csharp_setup_files/` folder bundled with the
coding-rules plugin (next to this rules file).

Required files:
- `icon_dark.ico` - Dark icon (for light Windows theme)
- `icon_light.ico` - Light icon (for dark Windows theme)

### Converting PNG to ICO

Use ImageMagick to convert PNG source files to multi-resolution ICO:

```batch
magick logo_dark.png -define icon:auto-resize=256,128,64,48,32,16 icon_dark.ico
magick logo_light.png -define icon:auto-resize=256,128,64,48,32,16 icon_light.ico
```

### Add Icons to Resources

In `Properties/Resources.resx`:

```xml
<data name="icon_dark" type="System.Resources.ResXFileRef, System.Windows.Forms">
  <value>..\data\icon_dark.ico;System.Drawing.Icon, System.Drawing, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b03f5f7f11d50a3a</value>
</data>
<data name="icon_light" type="System.Resources.ResXFileRef, System.Windows.Forms">
  <value>..\data\icon_light.ico;System.Drawing.Icon, System.Drawing, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b03f5f7f11d50a3a</value>
</data>
```

Update `Properties/Resources.Designer.cs`:

```csharp
internal static System.Drawing.Icon icon_dark {
    get {
        object obj = ResourceManager.GetObject("icon_dark", resourceCulture);
        return ((System.Drawing.Icon)(obj));
    }
}

internal static System.Drawing.Icon icon_light {
    get {
        object obj = ResourceManager.GetObject("icon_light", resourceCulture);
        return ((System.Drawing.Icon)(obj));
    }
}
```

### Theme Detection

Add Windows message constant and detection method:

```csharp
using Microsoft.Win32;

private const int WM_SETTINGCHANGE = 0x001A;

private bool IsWindowsUsingLightTheme()
{
    try
    {
        using (var key = Registry.CurrentUser.OpenSubKey(
            @"SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize", false))
        {
            var value = key?.GetValue("AppsUseLightTheme");
            return value != null && (int)value == 1;
        }
    }
    catch
    {
        return true; // Default to light theme if detection fails
    }
}
```

### Dynamic Icon Switching

```csharp
private NotifyIcon _trayIcon;

private void UpdateTrayIconForTheme()
{
    bool isLightTheme = IsWindowsUsingLightTheme();
    // Light theme = light taskbar background (use dark icon)
    // Dark theme = dark taskbar background (use light icon)
    Icon iconToUse = isLightTheme
        ? Properties.Resources.icon_dark
        : Properties.Resources.icon_light;

    if (_trayIcon != null)
    {
        _trayIcon.Icon = iconToUse;
    }
}
```

### Listen for Theme Changes

Override `WndProc` to detect when Windows theme changes:

```csharp
protected override void WndProc(ref Message m)
{
    if (m.Msg == WM_SETTINGCHANGE)
    {
        UpdateTrayIconForTheme();
    }
    base.WndProc(ref m);
}
```

### Full TrayManager Example

```csharp
public class TrayManager : IDisposable
{
    private NotifyIcon _trayIcon;
    private ContextMenuStrip _contextMenu;

    public event EventHandler ShowRequested;
    public event EventHandler ExitRequested;

    public TrayManager(Icon icon, Localization localization)
    {
        CreateContextMenu(localization);
        CreateTrayIcon(icon, localization);
    }

    private void CreateContextMenu(Localization localization)
    {
        _contextMenu = new ContextMenuStrip();

        var showItem = new ToolStripMenuItem(localization.Lang("tray.show"));
        showItem.Click += (s, e) => ShowRequested?.Invoke(this, EventArgs.Empty);
        _contextMenu.Items.Add(showItem);

        _contextMenu.Items.Add(new ToolStripSeparator());

        var exitItem = new ToolStripMenuItem(localization.Lang("tray.exit"));
        exitItem.Click += (s, e) => ExitRequested?.Invoke(this, EventArgs.Empty);
        _contextMenu.Items.Add(exitItem);
    }

    private void CreateTrayIcon(Icon icon, Localization localization)
    {
        _trayIcon = new NotifyIcon
        {
            Icon = icon,
            Text = localization.Lang("app.title"),
            ContextMenuStrip = _contextMenu,
            Visible = true
        };
        _trayIcon.DoubleClick += (s, e) => ShowRequested?.Invoke(this, EventArgs.Empty);
    }

    public void UpdateIcon(Icon icon)
    {
        if (icon != null && _trayIcon != null)
        {
            _trayIcon.Icon = icon;
        }
    }

    public void Dispose()
    {
        _trayIcon?.Dispose();
        _contextMenu?.Dispose();
    }
}
```

---

## 5 Essential Additional Rules

### 1) Use a consistent project structure

```
project/
├── data/
│   ├── icon_dark.ico
│   └── icon_light.ico
├── lang/
│   ├── en.json
│   └── languages.json
├── Properties/
│   ├── AssemblyInfo.cs
│   ├── Resources.resx
│   └── Resources.Designer.cs
├── Config/
│   ├── Constants.cs
│   └── AppSettings.cs
├── Form1.cs
├── Program.cs
└── MyApp.csproj
```

---

### 2) Centralize application settings

Use a settings class with JSON persistence:

```csharp
// Config/AppSettings.cs
using System.IO;
using Newtonsoft.Json;

public class AppSettings
{
    private static readonly string SettingsPath = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
        "MyApp", "settings.json");

    public static AppSettings Instance { get; } = Load();

    public string Language { get; set; } = "en";
    public bool MinimizeToTray { get; set; } = true;
    public bool LaunchOnStartup { get; set; } = false;

    private static AppSettings Load()
    {
        if (File.Exists(SettingsPath))
        {
            var json = File.ReadAllText(SettingsPath);
            return JsonConvert.DeserializeObject<AppSettings>(json) ?? new AppSettings();
        }
        return new AppSettings();
    }

    public void Save()
    {
        Directory.CreateDirectory(Path.GetDirectoryName(SettingsPath));
        File.WriteAllText(SettingsPath, JsonConvert.SerializeObject(this, Formatting.Indented));
    }
}
```

---

### 3) Embed dependencies with Costura.Fody

For single-file distribution, embed all DLLs into the executable.

#### Step 1: Install packages

Copy packages from an existing project or download:
- `packages/Fody.6.8.2/`
- `packages/Costura.Fody.5.7.0/`

#### Step 2: Create FodyWeavers.xml

Create `FodyWeavers.xml` in project folder:

```xml
<?xml version="1.0" encoding="utf-8"?>
<Weavers xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="FodyWeavers.xsd">
  <Costura />
</Weavers>
```

#### Step 3: Update .csproj (CRITICAL)

Add Costura.dll reference to ItemGroup with other References:

```xml
<Reference Include="Costura, Version=5.7.0.0, Culture=neutral, PublicKeyToken=null">
  <HintPath>..\packages\Costura.Fody.5.7.0\lib\netstandard1.0\Costura.dll</HintPath>
</Reference>
```

Include FodyWeavers.xml in an ItemGroup:

```xml
<None Include="FodyWeavers.xml" />
```

Add Import statements AFTER `<Import Project="$(MSBuildToolsPath)\Microsoft.CSharp.targets" />`:

```xml
<Import Project="..\packages\Costura.Fody.5.7.0\build\Costura.Fody.props" Condition="Exists('..\packages\Costura.Fody.5.7.0\build\Costura.Fody.props')" />
<Import Project="..\packages\Fody.6.8.2\build\Fody.targets" Condition="Exists('..\packages\Fody.6.8.2\build\Fody.targets')" />
<Import Project="..\packages\Costura.Fody.5.7.0\build\Costura.Fody.targets" Condition="Exists('..\packages\Costura.Fody.5.7.0\build\Costura.Fody.targets')" />
```

#### Verification

After build, the output folder should NOT contain any third-party DLLs - they are embedded in the .exe.

---

### 4) Handle startup registration properly

For "Launch on Windows startup" functionality:

```csharp
using Microsoft.Win32;

private const string StartupRegistryKey = @"Software\Microsoft\Windows\CurrentVersion\Run";
private const string StartupValueName = "MyApp";

private bool IsStartupEnabled()
{
    using (var key = Registry.CurrentUser.OpenSubKey(StartupRegistryKey, false))
    {
        return key?.GetValue(StartupValueName) != null;
    }
}

private void SetStartupEnabled(bool enable)
{
    using (var key = Registry.CurrentUser.OpenSubKey(StartupRegistryKey, true))
    {
        if (key == null) return;

        if (enable)
            key.SetValue(StartupValueName, Application.ExecutablePath);
        else
            key.DeleteValue(StartupValueName, false);
    }
}
```

---

### 5) Implement proper disposal pattern

All forms and managers should implement IDisposable:

```csharp
protected override void OnFormClosed(FormClosedEventArgs e)
{
    _timer?.Stop();
    _timer?.Dispose();
    _trayManager?.Dispose();
    base.OnFormClosed(e);
}
```

---

### 7) Required Batch Files

Every project must include these batch files in the `tools/` directory:

- `tools/run_tests.bat` - Runs the test suite
- `tools/build_release.bat` - Builds the release version

---

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

## Dark Theme UI (Optional)

For consistent dark theme in Windows Forms:

```csharp
// Colors
private static readonly Color DarkBackground = Color.FromArgb(30, 30, 30);
private static readonly Color DarkForeground = Color.White;
private static readonly Color DarkAccent = Color.FromArgb(60, 60, 60);

// Apply to form
this.BackColor = DarkBackground;
this.ForeColor = DarkForeground;

// Apply to controls
foreach (Control control in this.Controls)
{
    control.BackColor = DarkBackground;
    control.ForeColor = DarkForeground;
}
```

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
