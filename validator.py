BLOCKED_MODULES = {
    "os", "subprocess", "sys", "shutil",
    "socket", "requests", "urllib",
    "pathlib", "io", "builtins",
    "importlib", "ctypes", "multiprocessing"
}

BLOCKED_BUILTINS = {
    "exec", "eval", "compile",
    "open", "input", "__import__",
    "getattr", "setattr", "delattr",
    "globals", "locals", "vars"
}

class SafetyValidator(ast.NodeVisitor):
    def __init__(self):
        self.errors = []

    def visit_Import(self, node):
        for alias in node.names:
            module = alias.name.split('.')[0]
            if module in BLOCKED_MODULES:
                self.errors.append(f"Blocked import: '{alias.name}'")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            module = node.module.split('.')[0]
            if module in BLOCKED_MODULES:
                self.errors.append(f"Blocked import: 'from {node.module}'")
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            if node.func.id in BLOCKED_BUILTINS:
                self.errors.append(f"Blocked function: '{node.func.id}()'")
        self.generic_visit(node)