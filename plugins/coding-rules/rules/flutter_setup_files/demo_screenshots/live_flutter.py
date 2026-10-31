"""Copy-in template for seeding a local demo account before live screenshots.

Adjust the API and device URL constants for the host app. This launcher never
stores the returned token; it passes it directly to the Flutter process.
"""

import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from contextlib import redirect_stdout
from urllib.parse import urlsplit

DEFAULT_API_URL = "http://localhost/api/v1"
ANDROID_API_URL = "http://10.0.2.2/api"
WINDOWS_API_URL = "http://localhost/api"
SEED_PATH = "demo/seed"
MACHINE_EMAIL_SUFFIX = "@machine.local"
REQUEST_TIMEOUT_SECONDS = 30


def local_api_url() -> str | None:
    api_url = (os.environ.get("DEMO_API_URL") or DEFAULT_API_URL).strip().rstrip("/")
    parsed = urlsplit(api_url)
    is_loopback = parsed.hostname in ("localhost", "127.0.0.1", "::1")
    if parsed.scheme not in ("http", "https") or not is_loopback:
        print("ERROR: Demo accounts may only be created on a loopback API URL.")
        return None
    return api_url


def _request_json(request: urllib.request.Request) -> dict:
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise ValueError("The service returned an invalid JSON object.")
    return payload


def seed_request_body(admin_password: str) -> dict[str, str]:
    """Keep app-specific seed fields in this single copy-in extension point."""
    return {"admin_password": admin_password}


def _api_error_message(
    error: urllib.error.HTTPError, secrets: tuple[str, ...] = ()
) -> str:
    try:
        payload = json.loads(error.read().decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return "The local API returned an unreadable error response."
    message = payload.get("message") if isinstance(payload, dict) else None
    if not isinstance(message, str):
        return "The local API returned an error."
    for secret in secrets:
        if secret:
            message = message.replace(secret, "[redacted]")
    return message


def seed_demo_token(api_url: str, admin_password: str) -> str:
    """Seed one local account and verify its token resolves to that same account."""
    request = urllib.request.Request(
        f"{api_url}/{SEED_PATH}",
        data=json.dumps(seed_request_body(admin_password)).encode("utf-8"),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )
    seeded = _request_json(request)
    user, token = seeded.get("user"), seeded.get("token")
    valid_user = (
        isinstance(user, dict)
        and isinstance(user.get("id"), (str, int))
        and isinstance(user.get("email"), str)
    )
    if not valid_user:
        raise ValueError("The local API returned an invalid demo user.")
    if not isinstance(token, str) or not token:
        raise ValueError("The local API did not return a demo-account token.")

    verify_request = urllib.request.Request(
        f"{api_url}/auth/me",
        headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
    )
    try:
        current_user = _request_json(verify_request).get("user")
    except urllib.error.HTTPError as error:
        error._demo_secrets = (admin_password, token)
        raise
    identity_matches = (
        isinstance(current_user, dict)
        and current_user.get("id") == user["id"]
        and current_user.get("email") == user["email"]
    )
    if not identity_matches:
        raise ValueError("The local API token does not match the seeded demo account.")
    if not user["email"].endswith(MACHINE_EMAIL_SUFFIX):
        raise ValueError(
            "The local API demo account does not use the machine email suffix."
        )
    return token


def _device_id(arguments: list[str]) -> str | None:
    for index, argument in enumerate(arguments):
        if argument in ("-d", "--device-id") and index + 1 < len(arguments):
            return arguments[index + 1]
        if argument.startswith("--device-id="):
            return argument.partition("=")[2]
    return None


def _app_api_url(arguments: list[str]) -> str:
    if _device_id(arguments) == "windows":
        return os.environ.get("DEMO_WINDOWS_SERVER_URL") or WINDOWS_API_URL
    return os.environ.get("DEMO_APP_SERVER_URL") or ANDROID_API_URL


def main(arguments: list[str] | None = None) -> int:
    """Seed credentials then run FVM Flutter with machine-only defines."""
    flutter_arguments = list(sys.argv[1:] if arguments is None else arguments)
    admin_password = os.environ.get("DEMO_ADMIN_PASSWORD", "")
    if not admin_password:
        print("ERROR: Set DEMO_ADMIN_PASSWORD in tools/config.bat.", file=sys.stderr)
        return 1
    fvm = shutil.which("fvm")
    if fvm is None:
        print("ERROR: Could not find fvm on PATH.", file=sys.stderr)
        return 1
    try:
        with redirect_stdout(sys.stderr):
            api_url = local_api_url()
            if api_url is None:
                return 1
            token = seed_demo_token(api_url, admin_password)
    except urllib.error.HTTPError as error:
        secrets = (admin_password, *getattr(error, "_demo_secrets", ()))
        message = _api_error_message(error, secrets)
        print(
            f"ERROR: Local API request failed with status {error.code}: {message}",
            file=sys.stderr,
        )
        return 1
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR: Could not seed the local demo account: {error}", file=sys.stderr)
        return 1

    command = [
        fvm,
        "flutter",
        *flutter_arguments,
        f"--dart-define=DEMO_ACCOUNT_TOKEN={token}",
        f"--dart-define=API_SERVER_URL={_app_api_url(flutter_arguments)}",
    ]
    try:
        return subprocess.run(command, check=False).returncode
    except OSError as error:
        print(f"ERROR: Could not start Flutter: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
