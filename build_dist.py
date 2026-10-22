"""Build script preparing distribution assets for static hosting and GitHub Pages."""

import os
import sys
import json
import zipfile
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_ANALYZER_DIR = os.path.join(BASE_DIR, "static_analyzer")
SAMPLES_DIR = os.path.join(BASE_DIR, "samples")
WEB_DIR = os.path.join(BASE_DIR, "web")
DIST_DIR = os.path.join(BASE_DIR, "dist")


def build_samples_json(target_path: str) -> None:
    """Reads all sample .c files and outputs a JSON catalog."""
    samples = {}
    if os.path.isdir(SAMPLES_DIR):
        for fname in sorted(os.listdir(SAMPLES_DIR)):
            if fname.endswith(".c"):
                src = os.path.join(SAMPLES_DIR, fname)
                with open(src, "r", encoding="utf-8") as f:
                    samples[fname] = f.read()

    with open(target_path, "w", encoding="utf-8") as f:
        json.dump({"samples": samples}, f, indent=2)
    print(f"Generated {target_path} with {len(samples)} samples")


def build_analyzer_zip(target_path: str) -> None:
    """Packages the entire static_analyzer package into a zip archive."""
    with zipfile.ZipFile(target_path, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(STATIC_ANALYZER_DIR):
            for file in sorted(files):
                if file.endswith(".py"):
                    full_p = os.path.join(root, file)
                    rel_p = os.path.relpath(full_p, BASE_DIR)
                    z.write(full_p, rel_p)

    size = os.path.getsize(target_path)
    print(f"Generated {target_path} ({size} bytes, {size/1024:.1f} KB)")


def build_dist() -> None:
    """Builds complete dist directory suitable for GitHub Pages deployment."""
    if os.path.exists(DIST_DIR):
        shutil.rmtree(DIST_DIR)
    os.makedirs(DIST_DIR, exist_ok=True)

    # 1. Generate web assets into web/ first
    web_samples = os.path.join(WEB_DIR, "samples.json")
    web_zip = os.path.join(WEB_DIR, "static_analyzer.zip")
    build_samples_json(web_samples)
    build_analyzer_zip(web_zip)

    # 2. Copy web/ contents to dist/
    for item in os.listdir(WEB_DIR):
        src = os.path.join(WEB_DIR, item)
        dst = os.path.join(DIST_DIR, item)
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)

    # 3. Copy samples/ into dist/samples/
    dist_samples = os.path.join(DIST_DIR, "samples")
    shutil.copytree(SAMPLES_DIR, dist_samples)

    # 4. Add .nojekyll so GitHub Pages does not ignore underscore files
    nojekyll_path = os.path.join(DIST_DIR, ".nojekyll")
    with open(nojekyll_path, "w", encoding="utf-8") as f:
        f.write("")

    print(f"Successfully built distribution in {DIST_DIR}")


if __name__ == "__main__":
    build_dist()
