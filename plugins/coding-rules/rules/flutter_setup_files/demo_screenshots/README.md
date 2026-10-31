# Local demo screenshot kit

This copy-in kit gives a Flutter app a repeatable local demo account for live screenshots and iteration. GoRabbits is the reference implementation.

## Install

1. Copy `live_flutter.bat`, `live_flutter.py`, and `test_live_flutter.py` into the app's `tools/create_media/` folder.
2. Merge the settings in `config_example.bat` into `tools/config_example.bat`; set the local API URL and the app URLs for Android emulator and Windows.
3. Copy the values from the example into the ignored `tools/config.bat` and set `DEMO_ADMIN_PASSWORD` to the local API administrator password.
4. In `tools/create_media/<app>.json`, set the `live` block's launcher to `cmd /c tools\create_media\live_flutter.bat`.
5. Ensure the local API enables its demo seed route only in local configuration. The route must refuse non-loopback roots.

The launcher seeds a fresh account each time, verifies its identity through `/auth/me`, then passes its token to Flutter without saving or printing it. Adjust the URL constants in `live_flutter.py` to match the API routing in the app and API projects. Run `python -m unittest` in `tools/create_media/` for the launcher's network-free self-check.
