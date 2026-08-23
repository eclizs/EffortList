import ctypes
import os

from .parser import parse_header

path = os.path.abspath(os.path.dirname(__file__))

libtrie = ctypes.CDLL(os.path.join(path, "libtrie.so"))

libtrie.getNumChar.restype = ctypes.c_int
NUM_CHAR = libtrie.getNumChar()


class TrieNode(ctypes.Structure):
    pass


TrieNode._fields_ = [
    ("children", ctypes.POINTER(TrieNode) * NUM_CHAR),
    ("terminal", ctypes.c_bool),
    ("original", ctypes.c_char_p),
]


class WordList(ctypes.Structure):
    _fields_ = [
        ("entries", ctypes.POINTER(ctypes.c_char_p)),
        ("count", ctypes.c_int),
    ]

ctypes_map = {
    "int": ctypes.c_int,
    "unsigned int": ctypes.c_uint,
    "long": ctypes.c_long,
    "unsigned long": ctypes.c_ulong,
    "char": ctypes.c_char,
    "char*": ctypes.c_char_p,
    "unsigned char": ctypes.c_ubyte,
    "float": ctypes.c_float,
    "double": ctypes.c_double,
    "bool": ctypes.c_bool,
    "void": None,
}


def init_pointer_type(base_type, pointer_level: int):
    if pointer_level == 0:
        return base_type
    return ctypes.POINTER(init_pointer_type(base_type, pointer_level - 1))


def init_type(type_name: str):
    if type_name in ctypes_map:
        return ctypes_map[type_name]

    pointer_level = type_name.count("*")
    base_type = type_name.replace("*", "").strip()

    if base_type in ctypes_map:
        base = ctypes_map[base_type]
    elif base_type in globals():
        base = globals()[base_type]
    else:
        raise ValueError(f"Unknown C type: {type_name}")

    return init_pointer_type(base, pointer_level)


def init_function(name, argtypes: list, restype):
    func = getattr(libtrie, name)
    func.argtypes = argtypes
    func.restype = restype
    return func


def create_trie_root():
    return ctypes.POINTER(TrieNode)()


def init_trie():
    definitions = parse_header(os.path.join(path, "../include/trie.h"))
    return {
        name: init_function(
            name,
            [init_type(parameter) for parameter in parameters],
            init_type(return_type),
        )
        for name, parameters, return_type in definitions
    }
