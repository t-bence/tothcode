import hashlib
import json
import shlex
import time
from pathlib import Path

import docker
from docker.errors import DockerException, ImageNotFound
from docker.models.containers import Container

from . import ui

IMAGE = "agent-harness:latest"
RUNNER = "/agent/runner.py"
LABEL_KEY = "dev.tothcode.runner-hash"
RUNNER_PATH = Path(__file__).resolve().parent.parent / "sandbox" / "runner.py"


class Sandbox:
    def __init__(self, workspace: Path):
        self.workspace = workspace.resolve()
        self.client: docker.DockerClient | None = None
        self.container: Container | None = None

    def start(self) -> None:
        try:
            self.client = docker.from_env()
        except DockerException:
            raise RuntimeError(
                "Cannot connect to Docker. Is Docker Desktop running?\n"
                "Start it, then try again."
            )

        current_hash = self._overall_hash()
        short_hash = current_hash[:12]

        try:
            existing = self.client.images.get(IMAGE)
            stored_hash = existing.labels.get(LABEL_KEY) if existing.labels else None
            if stored_hash == current_hash:
                ui.sandbox_reusing(short_hash)
            else:
                reason = "runner.py changed" if stored_hash else "missing label"
                ui.sandbox_building(reason)
                self.client.images.build(
                    path=".",
                    tag=IMAGE,
                    labels={LABEL_KEY: current_hash},
                    quiet=True,
                )
        except ImageNotFound:
            ui.sandbox_building("first build")
            self.client.images.build(
                path=".",
                tag=IMAGE,
                labels={LABEL_KEY: current_hash},
                quiet=True,
            )

        ui.sandbox_starting()
        self.container = self.client.containers.run(
            IMAGE,
            command="tail -f /dev/null",
            volumes={str(self.workspace): {"bind": "/workspace", "mode": "rw"}},
            working_dir="/workspace",
            network_mode="none",
            mem_limit="512m",
            nano_cpus=1_000_000_000,
            cap_drop=["ALL"],
            security_opt=["no-new-privileges"],
            detach=True,
            remove=True,
        )
        self._wait_ready()
        ui.sandbox_ready(self.container.short_id)

    @staticmethod
    def _overall_hash() -> str:
        """Hash all files that affect the runner's behaviour inside the container."""
        # Hash of runner.py
        runner_hash = hashlib.sha256(RUNNER_PATH.read_bytes()).hexdigest()
        # Hash of the tool implementations (the only other code running inside the container)
        impl_path = Path(__file__).resolve().parent / "tools" / "impl.py"
        impl_hash = hashlib.sha256(impl_path.read_bytes()).hexdigest()
        combined = f"{runner_hash}:{impl_hash}".encode()
        return hashlib.sha256(combined).hexdigest()



    def _wait_ready(self, attempts: int = 20, interval: float = 0.1) -> None:
        for _ in range(attempts):
            try:
                code, _ = self.container.exec_run("true")
                if code == 0:
                    return
            except Exception:
                pass
            time.sleep(interval)

    def call(self, tool_name: str, args: dict) -> dict:
        if self.container is None or self.client is None:
            raise RuntimeError("Sandbox not started")

        payload = json.dumps({"tool": tool_name, "args": args})
        cmd = f"python3 {RUNNER} {shlex.quote(payload)}"

        _, raw = self.container.exec_run(cmd, workdir="/workspace")
        output = raw.decode("utf-8", errors="replace").strip()

        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return {"ok": False, "error": f"Runner returned non-JSON: {output!r}"}

    def stop(self) -> None:
        if self.container:
            try:
                self.container.stop(timeout=5)
            except Exception:
                pass
            self.container = None
            ui.sandbox_stopped()
