# Version
1

Increase this version number whenever this rule file changes.

# Arduino Web Server Rules

These rules apply on top of `ARDUINO_RULES.md` to any sketch that serves HTTP, whether through a W5x00 Ethernet shield or WiFi.

## Bound Every Request with One Deadline

Never read from a client in an unbounded `while (client.connected())`. Record one start time per client and enforce a deadline for the whole request. Check the deadline only when no byte is available, so buffered input is consumed without artificial delay, but never reset it per byte: a client trickling single bytes must not hold the board indefinitely.

```cpp
// include/config.h
namespace config {
    constexpr uint32_t REQUEST_TIMEOUT_MS = 2000;  // ms, whole-request deadline
}

const uint32_t requestStart = millis();
while (client.connected()) {
    if (client.available()) {
        const uint8_t ch = client.read();
        // Parse the bounded request line.
    } else if (millis() - requestStart > config::REQUEST_TIMEOUT_MS) {
        NetworkInfo::noteTimeout();
        break;
    }
}
```

One stalled client once froze LED updates, serial handling, and every later request until reset. Count each timeout so `/netinfo` exposes the problem.

## Use a Bounded Request Buffer

Keep only the request path from the request line in a fixed `char[]`, typically 64 bytes, and ignore header lines. Reject an over-long path; never write past the buffer. Follow **Memory Discipline** and **Input Validation at Boundaries** in `ARDUINO_RULES.md`.

## Keep Transport in the Server

`HttpServer` owns HTTP parsing, status and framing (`Content-Type: text/plain` and `Connection: close`), and `client.stop()`. One transport-independent `CommandHandler::execute(const char* path, Print& out)` owns the commands. The serial command reader calls the same function with `Serial` as `out`.

This gives HTTP and serial one command table and makes `execute` host-testable with a fake `Print`; follow **Host-Side Unit Tests** in `ARDUINO_RULES.md`.

## Whitelist Paths and Return Plain Answers

List every accepted path explicitly. Return one fixed plain-text rejection and the correct HTTP error status for an unknown path. Use the same `key: value` format for every status-like endpoint.

## Provide a Built-In `/netinfo` Endpoint

`/netinfo` reports the facts the selected network hardware can provide:

- link: `on`, `off`, or `unknown`; `unknown` is normal when the library cannot report it
- hardware or transport: `W5100`, `W5200`, `W5500`, `WiFi`, or `unknown`
- IP, subnet, gateway, and MAC address
- uptime in seconds
- `Connections`, `Requests`, and `Timeouts` counters
- last client as `ip:port`
- last request path, duration, and age

Never invent values for unsupported fields. `Connections >= Requests`; a gap means connections that did not produce a valid request, such as port scanners or aborted browser connections. `/netinfo` always answers: the debug switch only silences serial logs, because an explicitly requested endpoint disturbs nobody.

## Keep Diagnostics Free of Dependency Cycles

Use a standalone `NetworkInfo` module with static counters. The server calls `noteConnection`, `noteRequest`, and `noteTimeout`; the command handler calls `print(out)`. Neither module references the other.

## Use Compile-Time Switches with One Master

Extend the existing `include/debug.h` and `Log` setup instead of creating a parallel logger. `SERIAL_ENABLED` is the master for `Serial.begin`, serial commands, and serial-backed logging. `NETWORK_DEBUG` enables per-connection logs. `NETWORK_DEBUG_RAW` enables byte-by-byte request echo and defaults to `0` because it is very noisy.

```cpp
#define SERIAL_ENABLED 1
#define NETWORK_DEBUG 1
#define NETWORK_DEBUG_RAW 0

#if !SERIAL_ENABLED
  #undef DEBUG
  #undef NETWORK_DEBUG
  #define NETWORK_DEBUG 0
  #undef NETWORK_DEBUG_RAW
  #define NETWORK_DEBUG_RAW 0
#endif
```

Only switches consumed by `#if` are macros. Timing and configuration values remain `constexpr`. Feature code logs through `Log`, never raw `Serial` or a second family of logging macros. Follow **Serial Logging Strategy** in `ARDUINO_RULES.md`.

## Keep Network Log Lines Fixed

Use these forms:

```text
[NET] conn sock=<n> from <ip>:<port>
[NET] req "<path>" <ms> ms
[NET] timeout after <ms> ms
[NET] close sock=<n>
```

Save the socket number before `client.stop()`, which releases it. Measure request duration around `CommandHandler::execute()` so slow commands, including deliberate relay gaps, appear in the log.

## Check Hardware at Startup

Log missing network hardware and handle it according to whether networking is essential: halt only for a network-only device; otherwise keep offline and serial behavior alive. Log a link that is off at boot without halting, because the cable may be connected later.
