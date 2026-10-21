# Version
1

Increase this version number whenever this rule file changes.

# Kotlin Rules (Android / Gradle)

See `COMMON_RULES.md` for rules that apply to all languages.

---

## Build: Gradle Kotlin DSL

Use `*.gradle.kts`; commit the Gradle wrapper (`gradlew`, `gradlew.bat`, and `gradle/wrapper/`). Keep `local.properties` untracked. Declare plugin versions once in the root `plugins {}` block with `apply false`, or in `gradle/libs.versions.toml`; module build files apply plugins without repeating versions.

For JVM 17, configure Kotlin and Java compilation together:

```kotlin
import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
    id("com.android.library")
}

kotlin {
    compilerOptions { jvmTarget = JvmTarget.fromTarget("17") }
}

android {
    namespace = "com.example.library"
    compileSdk = 36
    defaultConfig { minSdk = 24 }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
```

Match the compile SDK, minimum SDK, Kotlin plugin, and Android Gradle Plugin versions to the project and its consumers.

---

## App Module vs Library Module

- An app applies `com.android.application`, declares `applicationId`, owns the UI and application entry point, and may own app-wide state.
- A library applies `com.android.library`, declares `namespace` and `minSdk`, has no `applicationId` or UI, and owns no global mutable state.
- Keep a library's public API small and document it. Enable `kotlin { explicitApi() }` where practical. Add only dependencies required by the library's contract.
- Pass configuration and collaborators (such as an HTTP client, logger sink, or base URL) through constructors. Do not create hidden clients or mutable singletons.
- A library must build and test on its own, with its own wrapper and `run-gradle.bat`. It must also work as a Git submodule included by an app with `include(":aichatapi")` (use the actual module name).

---

## Kotlin Language

- Prefer `val` and immutable `data class` models. Keep mutable state owned by the smallest responsible object.
- Do not use `!!` unless a one-line comment explains why the value is guaranteed non-null at that point.
- Model result and error variants with `sealed interface` or `sealed class`; make `when` exhaustive and omit `else` for sealed types.
- Use custom exception types for domain errors and catch only the specific exceptions a caller can handle.
- Use extension functions for genuine, reusable operations on a type; do not use them to hide substantial logic or dependencies.
- Do not use `object` singletons for mutable state; inject the owner instead. Do not use `GlobalScope`.

---

## Coroutines

- Make I/O APIs `suspend` when the project uses kotlinx-coroutines. Inject the dispatcher (defaulting to `Dispatchers.IO`) so tests can supply a test dispatcher.
- Give each coroutine scope a clear owner: use `viewModelScope`, `lifecycleScope`, or an injected scope that the owner cancels.
- A library without a coroutines dependency should document that blocking calls must run off the main thread. Do not add kotlinx-coroutines only to wrap blocking calls.

---

## KDoc

Use `/** ... */` KDoc on every public class, function, and property. Reference parameters with `[param]`. One sentence is enough for a simple member.

---

## Logging

Use the centralized `AppLogger` in `AppLogger.kt` from the COMMON_RULES logger table. It wraps `android.util.Log`; a library accepts an injectable sink and defaults to a no-op or `Log` sink so its consumer chooses where logs go. `android.util.Log` throws “not mocked” in local unit tests, so test logging through a fake sink.

---

## Testing

- Put local JVM unit tests in `src/test/` and use JUnit 4. They run without a device. Use `src/androidTest/` only when behavior truly requires Android runtime or hardware.
- Prefer small fakes over mocks for collaborators.
- `android.jar` contains stubs for some APIs, including `org.json`; add the real artifact as `testImplementation` when tests need it. Do not set `unitTests.isReturnDefaultValues = true`, which can hide missing behavior by returning zeros or `null`.
- Show live test progress in every module:

  ```kotlin
  import org.gradle.api.tasks.testing.Test
  import org.gradle.api.tasks.testing.logging.TestExceptionFormat

  tasks.withType<Test>().configureEach {
      testLogging {
          events("passed", "skipped", "failed")
          exceptionFormat = TestExceptionFormat.FULL
      }
  }
  ```

- Run Gradle with `--console=plain` so task and test output streams as readable lines.

---

## Lint and Format

Use the `org.jmailen.kotlinter` Gradle plugin for `lintKotlin` and `formatKotlin`. Run Android Lint with `lintDebug`. Never suppress a finding without a nearby comment explaining why.

---

## Self-Describing Classes

Implement COMMON_RULES “Self-Describing Classes” with an interface that exposes the fields a cross-cutting operation uses:

```kotlin
interface Searchable {
    fun searchableFields(): List<String>
}

data class Article(
    val title: String,
    val summary: String,
) : Searchable {
    override fun searchableFields(): List<String> = listOf(title, summary)
}
```

---

## Required Batch Files

Copy the bundled files from `kotlin_setup_files/`:

- `run-gradle.bat` at the project root invokes the Gradle wrapper and prints a heartbeat every 30 seconds. It requires `JAVA_HOME` to point to JDK 17 or newer; configure that on the machine, never hard-code its path in the repository.
- `tools/gradle-heartbeat.ps1` runs `gradlew.bat`, streams its output, and returns Gradle's exit code.
- `tools/run_tests.bat` runs `testDebugUnitTest --console=plain` across modules that define that task.
- `tools/run_analysis.bat` runs `lintKotlin lintDebug --console=plain`; `lintKotlin` requires the kotlinter plugin above.

When a project already has a working root `run-gradle.bat`, keep it and add only the missing helper and runner files.
