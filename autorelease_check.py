import setup
import codemodel

import autorelease
from packaging.version import Version

SETUP_VERSION  = autorelease.version.get_setup_version(None, directory='.')

repo_path = '.'
versions = {
    'package': codemodel.version.version,
    'setup.py': SETUP_VERSION,
}

RELEASE_BRANCHES = ['stable']
RELEASE_TAG = "v" + Version(SETUP_VERSION).base_version

if __name__ == "__main__":
    checker = autorelease.DefaultCheckRunner(
        versions=versions,
        setup=setup,
        repo_path='.'
    )
    checker.release_branches = RELEASE_BRANCHES + [RELEASE_TAG]

    tests = checker.select_tests_from_sysargs()
    n_fails = checker.run_as_test(tests)
