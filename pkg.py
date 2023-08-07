import os
import site
import zipfile
import shutil


def exec_file_wrapper(fpath, g_vars, l_vars):
    with open(fpath) as f:
        code = compile(f.read(), os.path.basename(fpath), "exec")
        exec(code, g_vars, l_vars)


def build_with_nuitka():
    command = (
        "nuitka  "
        "main.py "
        "--standalone "
        # "--onefile "
        "--nofollow-import-to=cv2,PIL "
        "--plugin-enable=pyside6 "
        # "--noinclude-qt-translations=True "
        "--include-data-dir=resources=resources "
        "--output-dir=build "
        "--output-filename=ArtifactScanner "
        "--windows-icon-from-ico=resources/bitmap/AppIcon.ico "
        "--disable-console "
        "--windows-uac-admin "
    )

    code = os.system(command)


def import_cv2():
    gvars = globals()
    gvars["BINARIES_PATHS"] = []
    gvars["PYTHON_EXTENSIONS_PATHS"] = []
    lvars = {}

    # get cv2 binaries path
    site_pkgs = site.getsitepackages()
    cv2_path = None
    for site_pkg in site_pkgs:
        cv2_path = os.path.join(site_pkg, "cv2")
        if os.path.exists(cv2_path):
            for cv2_file in os.listdir(cv2_path):
                if cv2_file.endswith(".py") and cv2_file.startswith("config"):
                    exec_file_wrapper(
                        os.path.join(cv2_path, cv2_file),
                        gvars,
                        lvars,
                    )
            break

    # copy cv2 to build/main.dist/cv2
    if cv2_path is not None:
        dst_path = shutil.copytree(cv2_path, "build/main.dist/cv2", dirs_exist_ok=True)
        print(f"Copy file from {cv2_path} to {dst_path}")
        binaries_paths = lvars["BINARIES_PATHS"]
        for binary_path in binaries_paths:
            dst_path = shutil.copytree(
                binary_path, "build/main.dist/cv2/.libs", dirs_exist_ok=True
            )
            print(f"Copy file from {binary_path} to {dst_path}")

        python_extension_rel_paths = [
            f"os.path.join(os.path.dirname(__file__), {os.path.relpath(p, cv2_path)})"
            for p in lvars["PYTHON_EXTENSIONS_PATHS"]
        ]

        config_content = f"""
import os

BINARIES_PATHS = [
    os.path.join(os.path.dirname(__file__), '.libs')
] + BINARIES_PATHS
"""
        config_3_content = f"""
import os
PYTHON_EXTENSIONS_PATHS = {str(python_extension_rel_paths)} + PYTHON_EXTENSIONS_PATHS
"""
        with open("build/main.dist/cv2/config.py", "w", encoding="utf8") as f:
            f.write(config_content)
        with open("build/main.dist/cv2/config-3.py", "w", encoding="utf8") as f:
            f.write(config_3_content)


def remove_unnecessary_resources():
    resources_path = "build/main.dist/resources"
    model_path = os.path.join(resources_path, "model", "onnx_crnnS05")
    for name in os.listdir(model_path):
        if name == "latest.onnx" or name == "dict.txt":
            continue
        os.remove(os.path.join(model_path, name))


def compress_dist():
    with zipfile.ZipFile("build/ArtifactScanner.zip", "w", zipfile.ZIP_LZMA) as zipf:
        output_fold = "build/main.dist"
        for root, dirs, files in os.walk(output_fold):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(
                    file_path,
                    os.path.relpath(file_path, output_fold),
                )


if __name__ == "__main__":
    build_with_nuitka()
    import_cv2()
    remove_unnecessary_resources()
    compress_dist()

