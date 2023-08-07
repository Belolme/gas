from PySide6.QtCore import QDir
import yaml
import os


_str_resources: dict | None = None


def load_string_resource(country_code="zh"):
    """
    Load string resources from a YAML file,
    with Chinese strings as the default resource.
    """
    resource_name = f"{country_code}.yaml"
    resource_dir = QDir("str:")
    if not resource_dir.exists(resource_name):
        resource_path = resource_dir.filePath("zh.yaml")
    else:
        resource_path = resource_dir.filePath(resource_name)

    with open(resource_path, "r", encoding="utf-8") as f:
        global _str_resources
        _str_resources = yaml.safe_load(f)

    # Add include files
    if _str_resources and _str_resources.get("include", None):
        for include_path in _str_resources["include"]:
            include_rel_path = os.path.join(
                os.path.dirname(resource_path),
                include_path,
            )

            with open(include_rel_path, "r", encoding="utf-8") as includef:
                include_content: dict | None = yaml.safe_load(includef)

            if include_content is None:
                print(f"Warning: empty include file {include_path}")
                continue

            for include_key, include_value in include_content.items():
                if include_key in _str_resources:
                    print(f"Warning: duplicated key {include_key} in {include_path}")
                else:
                    _str_resources[include_key] = include_value

        _str_resources.pop("include")


def load_string(name) -> str:
    if _str_resources is None:
        load_string_resource()

    assert _str_resources is not None
    return _str_resources[name]
