from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path


def load_client_module():
    module_path = Path(__file__).with_name("raspi_jpeg_capture_client.py")
    spec = importlib.util.spec_from_file_location("raspi_jpeg_capture_client", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeSocket:
    def __init__(self) -> None:
        self.timeout = "not-set"

    def settimeout(self, value):
        self.timeout = value


def test_default_command_idle_timeout_waits_forever() -> None:
    client = load_client_module()
    fake = FakeSocket()
    args = argparse.Namespace(command_idle_timeout_sec=0.0)

    client.configure_command_idle_timeout(fake, args)

    assert fake.timeout is None


def test_positive_command_idle_timeout_is_explicit_opt_in() -> None:
    client = load_client_module()
    fake = FakeSocket()
    args = argparse.Namespace(command_idle_timeout_sec=2.5)

    client.configure_command_idle_timeout(fake, args)

    assert fake.timeout == 2.5
