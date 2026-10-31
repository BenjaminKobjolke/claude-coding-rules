"""Tests for the copy-in live Flutter demo screenshot launcher."""

import json
import os
import subprocess
import unittest
import urllib.error
import urllib.request
from contextlib import redirect_stderr, redirect_stdout
from io import BytesIO, StringIO
from unittest.mock import patch

import live_flutter


class LiveFlutterTest(unittest.TestCase):
    @staticmethod
    def _seed_replies(token):
        user = {"id": 1, "email": "demo@machine.local"}
        return [
            BytesIO(json.dumps({"user": user, "token": token}).encode()),
            BytesIO(json.dumps({"user": user}).encode()),
        ]

    def setUp(self):
        self.environment = patch.dict(
            os.environ,
            {
                "DEMO_ADMIN_PASSWORD": "local-secret",
                "DEMO_API_URL": "http://localhost/api/v1",
                "DEMO_APP_SERVER_URL": "",
                "DEMO_WINDOWS_SERVER_URL": "",
            },
            clear=False,
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def test_missing_password_does_not_start_flutter(self):
        os.environ.pop("DEMO_ADMIN_PASSWORD", None)
        with patch.object(live_flutter.subprocess, "run") as run:
            self.assertEqual(live_flutter.main(["run"]), 1)
        run.assert_not_called()

    def test_non_loopback_url_is_rejected_without_request(self):
        os.environ["DEMO_API_URL"] = "https://example.com/api/v1"
        with patch.object(urllib.request, "urlopen") as urlopen:
            self.assertIsNone(live_flutter.local_api_url())
        urlopen.assert_not_called()

    def test_seed_body_and_identity_are_verified(self):
        calls = []
        def urlopen(request, timeout):
            calls.append((request, timeout))
            if request.get_method() == "POST":
                payload = {
                    "user": {"id": 17, "email": "demo-17@machine.local"},
                    "token": "fresh-token",
                }
            else:
                payload = {"user": {"id": 17, "email": "demo-17@machine.local"}}
            return BytesIO(json.dumps(payload).encode())
        with patch.object(urllib.request, "urlopen", side_effect=urlopen):
            token = live_flutter.seed_demo_token("http://localhost/api/v1", "pw")
        self.assertEqual(token, "fresh-token")
        seed, verify = calls
        self.assertEqual(seed[0].get_method(), "POST")
        self.assertEqual(seed[0].full_url, "http://localhost/api/v1/demo/seed")
        self.assertEqual(json.loads(seed[0].data), {"admin_password": "pw"})
        self.assertEqual(verify[0].full_url, "http://localhost/api/v1/auth/me")
        self.assertEqual(verify[0].get_header("Authorization"), "Bearer fresh-token")

    def test_mismatched_id_or_email_does_not_launch(self):
        users = (
            {"id": 18, "email": "demo-17@machine.local"},
            {"id": 17, "email": "person@example.com"},
        )
        for user in users:
            with self.subTest(user=user):
                seeded = {
                    "user": {"id": 17, "email": "demo-17@machine.local"},
                    "token": "token",
                }
                responses = [
                    BytesIO(json.dumps(seeded).encode()),
                    BytesIO(json.dumps({"user": user}).encode()),
                ]
                with (
                    patch.object(urllib.request, "urlopen", side_effect=responses),
                    patch.object(live_flutter.shutil, "which", return_value="fvm"),
                    patch.object(live_flutter.subprocess, "run") as run,
                ):
                    self.assertEqual(live_flutter.main(["run"]), 1)
                run.assert_not_called()

    def test_http_seed_error_reports_status_and_message_without_password(self):
        error = urllib.error.HTTPError(
            "http://localhost/api/v1/demo/seed",
            403,
            "Forbidden",
            {},
            BytesIO(b'{"message":"wrong admin password: local-secret"}'),
        )
        stderr = StringIO()
        with (
            patch.object(urllib.request, "urlopen", side_effect=error),
            patch.object(live_flutter.shutil, "which", return_value="fvm"),
            patch.object(live_flutter.subprocess, "run") as run,
            redirect_stderr(stderr),
        ):
            self.assertEqual(live_flutter.main(["run"]), 1)
        run.assert_not_called()
        self.assertIn("403", stderr.getvalue())
        self.assertIn("wrong admin password", stderr.getvalue())
        self.assertNotIn("local-secret", stderr.getvalue())

    def test_http_verification_error_does_not_expose_token(self):
        token = "private-token"
        error = urllib.error.HTTPError(
            "http://localhost/api/v1/auth/me",
            500,
            "Internal Server Error",
            {},
            BytesIO(b'{"message":"verification failed: private-token local-secret"}'),
        )
        seeded = {"user": {"id": 1, "email": "demo@machine.local"}, "token": token}
        replies = [BytesIO(json.dumps(seeded).encode()), error]
        stderr = StringIO()
        with (
            patch.object(urllib.request, "urlopen", side_effect=replies),
            patch.object(live_flutter.shutil, "which", return_value="fvm"),
            patch.object(live_flutter.subprocess, "run") as run,
            redirect_stderr(stderr),
        ):
            self.assertEqual(live_flutter.main(["run"]), 1)
        run.assert_not_called()
        self.assertNotIn(token, stderr.getvalue())
        self.assertNotIn("local-secret", stderr.getvalue())

    def test_device_defaults_overrides_and_flutter_exit_code(self):
        cases = (
            (["run", "-d", "emulator-5554"], live_flutter.ANDROID_API_URL),
            (["run", "-d", "windows"], live_flutter.WINDOWS_API_URL),
        )
        for arguments, default in cases:
            with self.subTest(arguments=arguments):
                seeded = {
                    "user": {"id": 1, "email": "demo@machine.local"},
                    "token": "private-token",
                }
                verified = {"user": {"id": 1, "email": "demo@machine.local"}}
                replies = [
                    BytesIO(json.dumps(seeded).encode()),
                    BytesIO(json.dumps(verified).encode()),
                ]
                with (
                    patch.object(
                        live_flutter.shutil, "which", return_value="C:/tools/fvm.exe"
                    ),
                    patch.object(
                        live_flutter.subprocess,
                        "run",
                        return_value=subprocess.CompletedProcess([], 7),
                    ) as run,
                    patch.object(urllib.request, "urlopen", side_effect=replies),
                ):
                    self.assertEqual(live_flutter.main(arguments), 7)
                command = run.call_args.args[0]
                self.assertEqual(
                    command[:4], ["C:/tools/fvm.exe", "flutter", *arguments[:2]]
                )
                self.assertIn("--dart-define=DEMO_ACCOUNT_TOKEN=private-token", command)
                self.assertIn(f"--dart-define=API_SERVER_URL={default}", command)
        os.environ["DEMO_APP_SERVER_URL"] = "http://10.0.2.2/custom-api"
        os.environ["DEMO_WINDOWS_SERVER_URL"] = "http://localhost/custom-api"
        overrides = (
            (["run", "-d", "emulator-5554"], "http://10.0.2.2/custom-api"),
            (["run", "-d", "windows"], "http://localhost/custom-api"),
        )
        for arguments, expected in overrides:
            with self.subTest(override=expected):
                replies = self._seed_replies("secret-token")
                with (
                    patch.object(live_flutter.shutil, "which", return_value="fvm"),
                    patch.object(
                        live_flutter.subprocess,
                        "run",
                        return_value=subprocess.CompletedProcess([], 0),
                    ) as run,
                    patch.object(urllib.request, "urlopen", side_effect=replies),
                ):
                    self.assertEqual(live_flutter.main(arguments), 0)
                api_define = f"--dart-define=API_SERVER_URL={expected}"
                self.assertIn(api_define, run.call_args.args[0])

    def test_seed_output_uses_stderr_and_hides_password_and_token(self):
        stdout, stderr = StringIO(), StringIO()
        replies = self._seed_replies("secret-token")
        with (
            patch.object(live_flutter.shutil, "which", return_value="fvm"),
            patch.object(
                live_flutter.subprocess,
                "run",
                return_value=subprocess.CompletedProcess([], 0),
            ),
            patch.object(urllib.request, "urlopen", side_effect=replies),
            redirect_stderr(stderr),
            redirect_stdout(stdout),
        ):
            self.assertEqual(live_flutter.main(["run", "--machine"]), 0)
        self.assertEqual(stdout.getvalue(), "")
        self.assertNotIn("local-secret", stderr.getvalue())
        self.assertNotIn("secret-token", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()

