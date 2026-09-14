#!/usr/bin/env python3
"""Reproduce native WebRTC smoothing experiments on macOS arm64.

Downloads are public, pinned and checked. No Reactor account or service is used.
Builds and logs stay in .local/experiments/webrtc-smoothing by default.
"""

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCES = Path(__file__).resolve().parent
TAG = "webrtc-7907-a5ddff60-p6"
ASSET = "reactor-webrtc-mac-arm64-release.tar.zst"
NATIVE_SHA = "0e3faf11e960d0784eb3551aeb5757a5b5bd12cd6a9e33b891ddebc7d9600bb6"
CRATE_SHA = "3c8fb671517bd85b278b31fc4ad2073f328fc2dc967d27439dd601f3465854d6"
GLUE_FILES = ["reactor_webrtc.cpp", "apple_hw/apple_hw_codec.h", "apple_hw/apple_hw_codec.mm"]
FRAMEWORKS = """Foundation CoreFoundation CoreAudio AudioToolbox CoreMedia
CoreVideo CoreGraphics CoreImage VideoToolbox AVFoundation AppKit IOSurface
IOKit Metal QuartzCore OpenGL ScreenCaptureKit Security SystemConfiguration""".split()


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def fetch(url, destination, expected):
    if not destination.exists():
        temporary = destination.with_suffix(destination.suffix + ".partial")
        request = urllib.request.Request(
            url, headers={"User-Agent": "VIbeParty-smoothing-experiment"}
        )
        with (
            urllib.request.urlopen(request, timeout=120) as response,
            temporary.open("wb") as output,
        ):
            shutil.copyfileobj(response, output)
        temporary.replace(destination)
    with destination.open("rb") as source:
        actual = hashlib.file_digest(source, "sha256").hexdigest()
    if actual != expected:
        raise RuntimeError(f"Checksum mismatch: {destination}; remove it before retrying")


def prepare(work):
    archive = work / ASSET
    fetch(
        f"https://github.com/reactor-team/reactor-webrtc/releases/download/{TAG}/{ASSET}",
        archive,
        NATIVE_SHA,
    )
    native = work / "native"
    sentinel = native / ".experiment-sha256"
    if not sentinel.exists() or sentinel.read_text().strip() != NATIVE_SHA:
        zstd = shutil.which("zstd")
        if not zstd:
            raise RuntimeError("zstd is required to unpack the native archive")
        tar_path = work / "native.tar"
        with tar_path.open("wb") as output:
            subprocess.run([zstd, "-d", "-c", str(archive)], stdout=output, check=True)
        native.mkdir(exist_ok=True)
        with tarfile.open(tar_path) as bundle:
            # The release also packages depot_tools' build-time Python runtime;
            # it is unnecessary to consume libwebrtc and includes read-only files.
            members = (
                member for member in bundle if "/third_party/depot_tools/" not in "/" + member.name
            )
            bundle.extractall(native, members=members, filter="data")
        tar_path.unlink()
        sentinel.write_text(NATIVE_SHA + "\n")
    crate = work / "reactor-webrtc-sys-0.16.0.crate"
    fetch("https://crates.io/api/v1/crates/reactor-webrtc-sys/0.16.0/download", crate, CRATE_SHA)
    with tarfile.open(crate) as bundle:
        for name in GLUE_FILES:
            destination = work / "vendor/glue" / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            source = bundle.extractfile(f"reactor-webrtc-sys-0.16.0/glue/{name}")
            if source is None:
                raise RuntimeError(f"Missing published source: {name}")
            with source:
                destination.write_bytes(source.read())


def build(work):
    include = work / "native/include"
    library = work / "native/lib/libwebrtc.a"
    if not library.exists():
        raise RuntimeError("Run the prepare command first")
    common = [
        "clang++",
        "-std=c++20",
        "-O2",
        "-DNDEBUG",
        "-DWEBRTC_MAC",
        "-DWEBRTC_POSIX",
        "-Wno-nullability-completeness",
    ]
    common += [
        f"-I{include / path}"
        for path in [".", "third_party/abseil-cpp", "third_party/libyuv/include"]
    ]
    frameworks = [item for name in FRAMEWORKS for item in ("-framework", name)]
    for name in ["smoothing_experiment", "loopback_experiment"]:
        command = common.copy()
        if name == "loopback_experiment":
            # Keep Objective-C categories in the static archive (codec metadata).
            command += [
                "-Wl,-ObjC",
                "-fobjc-arc",
                f"-I{include / 'sdk/objc/base'}",
                f"-I{include / 'sdk/objc'}",
                f"-I{work / 'vendor/glue'}",
            ]
        command.append(str(SOURCES / f"{name}.cc"))
        if name == "loopback_experiment":
            command.append(str(work / "vendor/glue/apple_hw/apple_hw_codec.mm"))
        command += [str(library), "-Wl,-dead_strip", "-o", str(work / name), *frameworks]
        save_json(work / f"{name}-build-command.json", command)
        with (work / f"{name}-build.log").open("w") as output:
            subprocess.run(
                command, stdout=output, stderr=subprocess.STDOUT, check=True, timeout=180
            )
        print(f"Built {name}", flush=True)


def run_case(work, name, executable, arguments):
    result = subprocess.run(
        [str(work / executable), *arguments], capture_output=True, text=True, timeout=40
    )
    (work / f"{name}.stdout").write_text(result.stdout)
    (work / f"{name}.stderr").write_text(result.stderr)
    if result.returncode:
        raise RuntimeError(f"{name}: exit {result.returncode}; inspect its stdout/stderr files")
    return json.loads(result.stdout)


def component(work):
    result = run_case(work, "component", "smoothing_experiment", [])
    save_json(work / "component-results.json", result)
    for row in result["results"]:
        print(row["profile"], "on" if row["smoothing"] else "off", row["delivered"])


def loopback(work, codec):
    results = []
    path = work / f"loopback-{codec}-results.json"
    for stall in [0, 150]:
        for mode in ["on", "off"]:
            name = f"loopback-{codec}-{mode}-{stall}"
            result = run_case(work, name, "loopback_experiment", [mode, str(stall), codec])
            ids = result["delivered_ids"]
            if ids != sorted(set(ids)):
                raise RuntimeError(f"{name}: duplicated or reordered frame markers")
            result["missing_ids"] = sorted(set(range(1, 159)) - set(ids))
            results.append(result)
            save_json(path, {"results": results})
            print(
                {key: value for key, value in result.items() if not key.endswith("_ids")},
                flush=True,
            )
    # Counts remain evidence, not a universal guarantee or an asserted expected
    # number of drops: real scheduler and codec behavior vary by host/run.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "build", "component", "loopback"])
    parser.add_argument(
        "--work-dir", type=Path, default=ROOT / ".local/experiments/webrtc-smoothing"
    )
    parser.add_argument("--codec", choices=["H264", "VP8"], default="H264")
    args = parser.parse_args()
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        parser.error("This pinned native build supports macOS arm64 only")
    work = args.work_dir.resolve()
    work.mkdir(parents=True, exist_ok=True)
    if args.command == "loopback":
        loopback(work, args.codec)
    else:
        {"prepare": prepare, "build": build, "component": component}[args.command](work)


if __name__ == "__main__":
    main()
