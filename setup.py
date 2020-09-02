import os

from setuptools import find_packages, setup
from setuptools.version import __version__ as setuptools_version

if tuple(map(int, setuptools_version.split("."))) < (40, 0):
    import sys

    python = sys.executable
    try:
        s = os.system('{} -m pip install "setuptools>=40"'.format(python))
        if s != 0:
            raise Exception
    except Exception:
        raise Exception("Setuptools>40 have to be installed")

    os.execl(python, python, *sys.argv)


with open(os.path.join("version.txt")) as version_file:
    version_from_file = version_file.read().strip()

with open("requirements.txt") as f_required:
    required = f_required.read().splitlines()

with open("test_requirements.txt") as f_tests:
    required_for_tests = f_tests.read().splitlines()

setup(
    name="cloudshell-cp-openstack",
    url="http://www.qualisystems.com/",
    author="QualiSystems",
    author_email="info@qualisystems.com",
    packages=find_packages(),
    install_requires=required,
    tests_require=required_for_tests,
    python_requires="~=3.7",
    version=version_from_file,
    package_data={"": ["*.txt"]},
    description="CloudShell Cloud Provider OpenStack package",
    include_package_data=True,
)
