#define PY_SSIZE_T_CLEAN
#include <Python.h>

static struct PyModuleDef _tspack_module = {
    PyModuleDef_HEAD_INIT,
    "_tspack",
    "Merged tree-sitter languages (C-level container).",
    -1,
    NULL, NULL, NULL, NULL, NULL
};

PyMODINIT_FUNC
PyInit__tspack(void)
{
    return PyModule_Create(&_tspack_module);
}