# Version
1

Increase this version number whenever this rule file changes.

# Unity C# Rules

See `COMMON_RULES.md` for rules that apply to all languages.

---

## 1. MonoBehaviour Lifecycle

### Cache Component References in Awake/Start

Cache all component references in `Awake()` or `Start()`. Never call `GetComponent<T>()`,
`Find()`, or `FindFirstObjectByType()` in `Update()` or any per-frame method.

Use `Awake()` for self-initialization (caching own components) and `Start()` for cross-references
to other GameObjects. This ensures dependencies are ready when `Start()` runs.

```csharp
private AudioSource _audioSource;
private Transform _cachedTransform;

private void Awake()
{
    _audioSource = GetComponent<AudioSource>();
    _cachedTransform = transform;
}
```

### Unsubscribe Events in OnDestroy

Always unsubscribe from events in `OnDestroy()`. Pair every `+=` with a `-=` to prevent memory
leaks and null reference exceptions.

```csharp
private void OnEnable()
{
    _inputHandler.OnTriggerPressed += HandleTrigger;
}

private void OnDisable()
{
    _inputHandler.OnTriggerPressed -= HandleTrigger;
}
```

### Use RequireComponent

Use `[RequireComponent(typeof(T))]` when a MonoBehaviour depends on another component on the
same GameObject. This prevents misconfigured prefabs.

```csharp
[RequireComponent(typeof(AudioSource))]
public class AudioManager : MonoBehaviour { }
```

### Explicit Initialize Methods

Prefer explicit `Initialize()` methods over constructor-like patterns for injecting dependencies
between MonoBehaviours. Document required initialization order.

```csharp
public void Initialize(StateController stateController, AudioManager audioManager)
{
    _stateController = stateController;
    _audioManager = audioManager;
}
```

### No String-Based Invoke

Never use `Invoke("MethodName", delay)` with string method names. Use coroutines or
`Invoke(nameof(Method), delay)` for type safety.

---

## 2. Performance — Update Loop and Caching

### No Empty Update Methods

Remove empty `Update()`, `FixedUpdate()`, or `LateUpdate()` methods. Unity calls these via
reflection even if they are empty, adding per-frame overhead.

### Timer-Based Guards

For logic that does not need to run every frame, use timer-based guards or coroutines with
`WaitForSeconds`:

```csharp
private float _lastCheck;
private const float CheckInterval = 0.5f;

private void Update()
{
    if (Time.time - _lastCheck < CheckInterval) return;
    _lastCheck = Time.time;
    // Perform periodic check
}
```

### Cache Frequently Accessed Properties

Cache `Transform`, `Camera.main` (use a static finder/cache), and controller input devices.
Re-acquire only when invalid.

```csharp
// Bad
void Update() { Camera.main.transform.position; }

// Good — use a cached reference
private Camera _mainCamera;
void Start() { _mainCamera = Camera.main; }
```

### Use CompareTag

Use `CompareTag("tag")` instead of `gameObject.tag == "tag"` to avoid string allocation.

### Prefer Index-Based Loops

When iterating arrays in `Update()`, use index-based `for` loops instead of `foreach` to avoid
enumerator allocation on older Unity versions.

---

## 3. Memory and GC

### No Allocations in Hot Paths

Never allocate in hot paths (`Update`, `LateUpdate`, `FixedUpdate`). Common allocations to avoid:

- `string.Format`, string concatenation, `ToString()`
- `new List<T>()`, `new Dictionary<T,T>()`
- LINQ queries (`.Where()`, `.Select()`, etc.)
- Lambda closures that capture variables
- `GetComponentsInChildren()` called per frame
- `ToArray()` or `ToList()` on collections

### Pre-Allocate Reusable Collections

Pre-allocate collections as class fields and reuse them instead of creating new ones each frame:

```csharp
private readonly List<Vector3> _reusablePoints = new List<Vector3>();

private void ProcessPoints(List<Vector3> source)
{
    _reusablePoints.Clear();
    _reusablePoints.AddRange(source);
    // Work with _reusablePoints
}
```

### Strip Debug.Log from Builds

Use `Debug.Log` only during development. Wrap verbose logging in
`#if UNITY_EDITOR || DEVELOPMENT_BUILD` or use `[System.Diagnostics.Conditional("UNITY_EDITOR")]`
to strip logs from release builds.

```csharp
[System.Diagnostics.Conditional("UNITY_EDITOR")]
private static void LogDebug(string message)
{
    Debug.Log(message);
}
```

### Prefer Struct for Small Data

Use `struct` for small, short-lived value types (transform snapshots, raycast data). Use `class`
for shared mutable state or objects with reference semantics.

---

## 4. Serialization and Inspector

### SerializeField Over Public

Prefer `[SerializeField] private` over `public` fields for Inspector-exposed values. Public fields
should only be used when other scripts genuinely need direct access.

```csharp
// Bad
public float speed = 5f;

// Good
[SerializeField] private float _speed = 5f;
```

### Organize Inspector Fields

Add `[Header("Section")]` and `[Tooltip("...")]` to group and document Inspector fields.
Use `[Range(min, max)]` for numeric fields that have valid bounds.

```csharp
[Header("Movement")]
[Tooltip("Movement speed in meters per second")]
[SerializeField, Range(0f, 20f)] private float _speed = 5f;
```

### Use Enums for Modes

Use enums for mode/state selection in the Inspector instead of booleans or magic numbers.

### Hide Internal State

Never expose implementation details in the Inspector. Internal state variables should be private
without `[SerializeField]`.

---

## 5. Architecture — Events and State

### Event-Driven Communication

Use `System.Action` events or `UnityEvent` for inter-component communication. Never poll another
component's state in `Update()` when an event can signal the change.

```csharp
public event Action<AppState> OnStateChanged;

private void ChangeState(AppState newState)
{
    _currentState = newState;
    OnStateChanged?.Invoke(newState);
}
```

### Interfaces for Swappable Behaviors

Define interfaces for behaviors that need multiple implementations (e.g., `IInputHandler` for
XR vs keyboard, `IVideoController` for different video backends). This enables editor testing
with fallback implementations.

### Explicit State Machines

State machines should be explicit: define states as an enum, transitions as methods, and
broadcast state changes via events.

### Focused MonoBehaviours

Keep MonoBehaviours focused on a single responsibility. Extract logic into plain C# classes or
static utilities when it does not need MonoBehaviour lifecycle hooks.

---

## 6. Coroutines and Async

### Store Coroutine References

Always store coroutine references so they can be stopped cleanly. Stop coroutines before starting
new ones to prevent duplicates.

```csharp
private Coroutine _fadeCoroutine;

private void StartFade(float target)
{
    if (_fadeCoroutine != null)
        StopCoroutine(_fadeCoroutine);
    _fadeCoroutine = StartCoroutine(FadeRoutine(target));
}
```

### UnityWebRequest in Coroutines

For network requests, use `UnityWebRequest` inside coroutines with `yield return`. Do not use
`System.Net.Http.HttpClient` or `Task.Run()` in Unity.

```csharp
private IEnumerator SendRequest(string url)
{
    using (var request = UnityWebRequest.Get(url))
    {
        yield return request.SendWebRequest();
        if (request.result == UnityWebRequest.Result.Success)
            ProcessResponse(request.downloadHandler.text);
    }
}
```

### Cancellable Coroutines

If a coroutine should be cancellable, check a boolean flag or stop it by reference. Avoid
orphaned coroutines that outlive their purpose.

### Prefer Coroutines Over async/await

Use coroutines as the primary async pattern in Unity. They integrate naturally with the Unity
lifecycle, support `WaitForSeconds`, `WaitForEndOfFrame`, and `yield return` on Unity operations.
Only use `async/await` when interfacing with external libraries that require it.

---

## 7. XR / VR Specific (Meta Quest)

### Abstract Input Handling

Abstract input handling behind an interface. Provide separate implementations for XR controllers
and keyboard (editor testing). Use `#if UNITY_EDITOR` to select the default.

```csharp
public interface IInputHandler
{
    event Action OnTriggerPressed;
    event Action OnButtonAPressed;
    void UpdateInput();
}
```

### Controller Device Re-Acquisition

Use `UnityEngine.XR.InputDevices` for controller input. Re-acquire the device handle each frame
if `!controller.isValid`. Use button-down detection (current frame pressed AND previous frame
not pressed) to avoid repeated triggers from held buttons.

```csharp
private InputDevice _controller;

private void AcquireController()
{
    if (_controller.isValid) return;
    var devices = new List<InputDevice>();
    InputDevices.GetDevicesAtXRNode(XRNode.RightHand, devices);
    if (devices.Count > 0)
        _controller = devices[0];
}
```

### Platform Guards for Quest APIs

Access Meta Quest APIs (`OVRManager`, `OVRPassthroughLayer`) only inside `#if UNITY_ANDROID`
guards. Provide editor fallback behavior with mock values.

```csharp
private float GetBatteryLevel()
{
    #if UNITY_ANDROID
    return OVRManager.batteryLevel;
    #else
    return 1.0f; // Mock value for editor
    #endif
}
```

### Recenter Tracking Pose

Recenter the tracking pose on startup with `OVRManager.display.RecenterPose()` to prevent
orientation drift on Quest.

### Passthrough Camera Setup

For passthrough (mixed reality), manage camera clear flags:
- Passthrough mode: `CameraClearFlags.SolidColor` + `Color.clear`
- Immersive VR: `CameraClearFlags.Skybox`

### Single-Controller Design

Design all interactions for single-controller operation. Map primary actions to trigger,
secondary to A/B buttons, and navigation to grip. Use cooldown timers on trigger inputs to
prevent accidental double-activations.

---

## 8. Shaders and Rendering (Quest Mobile)

### URP HLSL Only

Use URP (Universal Render Pipeline) HLSL shaders, not legacy CG/surface shaders. Include
`Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl`.

```hlsl
// Good — URP HLSL
#include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

// Bad — Legacy
#include "UnityCG.cginc"
```

### SRP Batcher Compatibility

Use `CBUFFER_START(UnityPerMaterial)` / `CBUFFER_END` for SRP Batcher compatibility on all
material properties:

```hlsl
CBUFFER_START(UnityPerMaterial)
    float4 _Color;
    float _Intensity;
CBUFFER_END
```

### Minimize Shader Passes

For Quest mobile GPU: minimize shader passes, avoid alpha testing where possible (use alpha
blending), keep fragment shaders simple, and avoid dependent texture reads.

### Correct Transparency Tags

Tag transparent shaders correctly:

```hlsl
Tags { "RenderType"="Transparent" "Queue"="Transparent" }
Blend SrcAlpha OneMinusSrcAlpha
ZWrite Off
```

### Multiview Stereo Rendering

Target single-pass instanced (multiview) stereo rendering for Quest. Use `unity_StereoEyeIndex`
only in shaders that need per-eye variation.

---

## 9. Singleton Pattern

If a singleton is truly needed (e.g., a manager that persists across scenes), use this pattern:

```csharp
public class GameManager : MonoBehaviour
{
    public static GameManager Instance { get; private set; }

    private void Awake()
    {
        if (Instance != null && Instance != this)
        {
            Destroy(gameObject);
            return;
        }
        Instance = this;
        DontDestroyOnLoad(gameObject);
    }
}
```

Minimize singletons — most managers can be scene-scoped without `DontDestroyOnLoad`. Prefer
dependency injection via `Initialize()` methods or ScriptableObject-based shared state.

---

## 10. Scene and Prefab Management

### Group Inspector Arrays by Purpose

Group Inspector-assignable object arrays by purpose using `[Header]` attributes:

```csharp
[Header("Scene Content")]
[SerializeField] private GameObject[] _sceneObjects;

[Header("Passthrough Content")]
[SerializeField] private GameObject[] _passthroughObjects;
```

### VisibilityMode Enum

Use an enum to support both renderer-based toggling (finer control) and GameObject-based
toggling (simpler):

```csharp
public enum VisibilityMode { GameObject, Renderer }
```

### Cache Renderer Arrays

Cache `Renderer[]` arrays at startup when managing visibility of object groups. Never call
`GetComponentsInChildren<Renderer>()` at runtime during state transitions.

---

## 11. Platform-Specific Code

### Preprocessor Directives

Use `#if UNITY_EDITOR` for editor-only logic (mock values, gizmos, menu items). Use
`#if UNITY_ANDROID` for Quest-specific APIs. Always provide an `#else` fallback with meaningful
behavior or logging.

### Editor Script Separation

Editor-only scripts must be placed in an `Editor/` folder or wrapped entirely in
`#if UNITY_EDITOR` / `#endif`.

---

## 12. Assembly Definitions

Create assembly definitions (`*.asmdef`) to separate code into compilation units:

```
Assets/
  Scripts/
    Runtime/    → MyProject.Runtime.asmdef
    Editor/     → MyProject.Editor.asmdef
    Tests/      → MyProject.Tests.asmdef
```

This reduces recompilation time and enforces dependency direction. The Editor assembly should
reference Runtime but not vice versa.

---

## 13. Testing

Use Unity Test Framework for testing. At minimum, test state machine transitions, input handler
event firing, and any pure logic (math utilities, data transformations).

- Use `[Test]` for synchronous logic tests
- Use `[UnityTest]` for coroutine-based tests that need to yield

```csharp
[Test]
public void StateController_ChangeState_FiresEvent()
{
    var controller = new StateController();
    AppState received = default;
    controller.OnStateChanged += s => received = s;

    controller.ChangeState(AppState.Playing);

    Assert.AreEqual(AppState.Playing, received);
}
```

Provide test runner scripts:
- `tools/run_tests.bat` — runs EditMode and PlayMode tests

---

## 14. Logging Convention

### Class Name Prefix

Prefix all `Debug.Log` messages with the class name in brackets:

```csharp
Debug.Log("[AudioManager] Playing clip: " + clipName);
Debug.LogWarning("[MainController] State transition skipped");
Debug.LogError("[VideoPlayer] Failed to prepare video");
```

### Log Levels

- `Debug.Log` — informational messages
- `Debug.LogWarning` — recoverable issues
- `Debug.LogError` — unrecoverable errors

### Central Logger Class

Route all logging through one static helper named **`GameLog`** (`GameLog.cs`). Never call
`Debug.Log`/`LogWarning`/`LogError` directly from gameplay code — only `GameLog` wraps them.
This gives a single enable/level toggle and one place to strip logs from production.

```csharp
GameLog.Info("AudioManager", "Playing clip: " + clipName);
GameLog.Warning("MainController", "State transition skipped");
GameLog.Error("VideoPlayer", "Failed to prepare video");
```

### Strip from Production

Inside `GameLog`, use `[System.Diagnostics.Conditional]` (or `#if`) to strip logs from
production builds targeting Quest, where console overhead affects frame rate.

```csharp
[System.Diagnostics.Conditional("UNITY_EDITOR")]
[System.Diagnostics.Conditional("DEVELOPMENT_BUILD")]
public static void Info(string tag, string message) => Debug.Log($"[{tag}] {message}");
```

---

## 15. Project Directory Structure

Maintain this folder structure under Assets:

```
Assets/
  Audio/
  Editor/             # Editor-only scripts
  Materials/
  Models/
  Plugins/
  Prefabs/
  Resources/          # Only for assets loaded via Resources.Load
  Scenes/
  Scripts/            # Runtime scripts
  Settings/
  Shaders/
  StreamingAssets/
  Textures/
  XR/
```

---

## 16. ScriptableObjects for Configuration

Use `ScriptableObject` assets for configuration data that is shared across scenes or frequently
tweaked: audio timing, input cooldown values, battery thresholds, fade durations.

```csharp
[CreateAssetMenu(fileName = "AppConfig", menuName = "Config/App Config")]
public class AppConfig : ScriptableObject
{
    [Header("Audio")]
    public float fadeInDuration = 1f;
    public float fadeOutDuration = 0.5f;

    [Header("Input")]
    public float triggerCooldown = 0.3f;

    [Header("Battery")]
    public float lowBatteryThreshold = 0.2f;
}
```

This avoids hardcoding values in MonoBehaviours and enables non-programmer editing via the
Inspector without touching code.

---

## Required Batch Files

Every Unity project must include these batch files in the `tools/` directory:

- `tools/run_tests.bat` — runs EditMode and PlayMode tests via Unity CLI
