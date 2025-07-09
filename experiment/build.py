import subprocess


IMAGE_TAG = "cockroach-builder"


def build_container():
    dockerfile_path = "./../build/crdb/dockerfile"
    context_path = "./.."

    cmd = ["docker", "build", "-f", dockerfile_path, "-t", IMAGE_TAG, context_path]

    subprocess.run(
        cmd,
        check=True,
    )


def run_container():
    workdir_path = "/app/cockroach"
    volume_app_path = "./../:/app"
    volume_bzlhome_path = "bzlhome:/home/roach:delegated"
    user = "1000:1000"

    cmd = [
        "docker",
        "run",
        "--rm",
        "-it",
        "--workdir",
        workdir_path,
        "-v",
        volume_app_path,
        "-v",
        volume_bzlhome_path,
        "-u",
        user,
        IMAGE_TAG,
    ]

    subprocess.run(
        cmd,
        check=True,
    )
