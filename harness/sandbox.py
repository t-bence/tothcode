import json
import shlex
from pathlib import Path

import docker
from docker.errors import DockerException, ImageNotFound
from docker.models.containers import Container
from rich.console import Console

# Separate stderr console so sandbox status messages don't mix with agent output
console = Console(stderr=True)

IMAGE = "agent-harness:latest"
RUNNER = "/agent/runner.py"


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

        try:
            self.client.images.get(IMAGE)
        except ImageNotFound:
            console.print("[dim]Building sandbox image…[/]")
            self.client.images.build(path=".", tag=IMAGE, quiet=True)

        console.print("[dim]Starting sandbox container…[/]")
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
        console.print(f"[green]Sandbox ready[/] [dim](id: {self.container.short_id})[/]")

    def _wait_ready(self, attempts: int = 20, interval: float = 0.1) -> None:
        import time
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
            console.print("[dim]Sandbox stopped.[/]")
