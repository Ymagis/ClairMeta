import os
import doctest
import importlib


def load_tests(loader, tests, ignore):
    finder = doctest.DocTestFinder(exclude_empty=False)

    path_tests = os.path.abspath(os.path.dirname(__file__))
    path_src = os.path.join(os.path.dirname(path_tests), 'clairmeta')

    for dirpath, dirnames, filenames in os.walk(path_src):
        py_files = [f for f in filenames if f.endswith('.py')]

        if dirpath == path_src:
            module_prefix = 'clairmeta.'
        else:
            rel_path = os.path.relpath(dirpath, path_src)
            module_prefix = 'clairmeta.' + rel_path + '.'

        for f in py_files:
            mod = importlib.import_module(module_prefix + f[:-3])
            tests.addTests(doctest.DocTestSuite(mod, test_finder=finder))

    return tests
