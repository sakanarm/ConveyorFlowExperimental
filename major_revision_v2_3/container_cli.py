"""Task-selected OCI CLI, preserving Docker as the default backend."""

import os
import re
import subprocess


def executable() -> str:
    name = os.environ.get("CONVEYORFLOW_CONTAINER_COMMAND", "docker")
    if name not in {"docker", "podman"}:
        raise ValueError("container command must be docker or podman")
    return name


def canonical_image_id(value: str) -> str:
    value = value.strip()
    if re.fullmatch(r"[0-9a-f]{64}", value):
        value = "sha256:" + value
    return value


def working_directory() -> str:
    # Older Buildah can preserve WORKDIR metadata without creating /work.
    # /tmp is a bounded writable tmpfs; source/input mounts stay read-only.
    return "/tmp" if executable() == "podman" else "/work"


def runtime_version(environment: dict, *, timeout: int = 30) -> str:
    name = executable()
    command = [name, "--version"] if name == "podman" else [name, "info", "--format", "{{.ServerVersion}}"]
    result = subprocess.run(command, capture_output=True, text=True,
                            timeout=timeout, env=environment)
    value = result.stdout.strip()
    if name == "podman":
        value = value.removeprefix("podman version ")
    if result.returncode != 0 or not re.fullmatch(r"\d+\.\d+(?:\.\d+)?[^\s]*", value):
        raise RuntimeError("container runtime is unavailable; no provider call was made")
    return value
