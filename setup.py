from setuptools import setup, find_packages
from codecs import open
from os import path
import sys
from astra import __version__

from setuptools.command.test import test as TestCommand

here = path.abspath(path.dirname(__file__))


class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, because outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.test_args)
        sys.exit(errno)


# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='redis-astra',
    version=__version__,
    description='ORM for Redis',
    long_description=long_description,
    url='https://github.com/pilat/redis-astra',
    download_url='https://github.com/pilat/redis-astra/tarball/{0}'
        .format(__version__),
    author='Vladimir K Urushev',
    author_email='urushev@yandex.ru',
    maintainer='Vladimir K Urushev',
    maintainer_email='urushev@yandex.ru',
    keywords=['Redis', 'ORM'],
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        ],
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    install_requires=['redis>=2.9.1', 'PyDispatcher>=2.0.5', 'six>=1.10.0'],
    extras_require={
        'dev': ['check-manifest'],
        'test': ['coverage', 'mock'],
    },
    tests_require=['pytest>=2.5.0'],
    cmdclass={'test': PyTest},
)
