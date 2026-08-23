import re


def parse_header(filepath: str) -> list:
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    functions = []
    func_pattern = re.compile(
        r"(\w[\w\s\*]+?)\s+(\w+)\s*\(([^)]*)\)\s*;"
    )

    for match in func_pattern.finditer(content):
        return_val, func_name, func_param = match.groups()
        return_val = return_val.strip()
        func_param = [p.strip() for p in func_param.split(",") if p.strip()]

        for i, param in enumerate(func_param):
            match = re.fullmatch(r"(.+?)([A-Za-z_]\w*)", param)

            if match is None:
                raise ValueError(f"Could not parse parameter: {param}")

            param_type = match.group(1).strip()
            param_type = re.sub(r"\s*\*\s*", "*", param_type)
            func_param[i] = re.sub(r"\s+", " ", param_type)

        if return_val.split()[-1] in ("typedef", "struct", "enum"):
            continue

        functions.append((func_name, func_param, return_val))

    return functions
