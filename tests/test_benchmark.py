"""Include the isolated benchmark suite in the existing repository-wide discovery."""

import unittest

from benchmarks.renters.tests import test_dataset, test_scoring


def load_tests(loader, tests, pattern):
    suite = unittest.TestSuite()
    for module in (test_dataset, test_scoring):
        suite.addTests(loader.loadTestsFromModule(module))
    return suite
