#!/usr/bin/env python
# -*- coding: utf-8 -*-

# {# pkglts, pysetup.kwds
# format setup arguments

from setuptools import setup, find_packages


short_descr = "TODO"
readme = open('README.md').read()


# find version number in src/openalea/core/version.py
version = {}
with open("initialize/version.py") as fp:
    exec(fp.read(), version)

# find packages
pkgs = find_packages('initialize')


setup_kwds = dict(
    name='data_utility.initialize',
    version=version["__version__"],
    description=short_descr,
    long_description=readme,
    author="Tristan Gérault, Christophe Pradal",
    author_email="tristan.gerault@inrael.fr, christophe.pradal@cirad.fr",
    url='https://github.com/GeraultTr/initialize.git',
    license='cecill-c',
    zip_safe=False,

    packages=pkgs,
    namespace_packages=['data_utility'],
    package_dir={'': 'initialize'},
    setup_requires=[
        "pytest-runner",
        ],
    install_requires=[
        ],
    tests_require=[
        "coverage",
        "pytest",
        "pytest-cov",
        "pytest-mock",
        "sphinx",
        ],
    entry_points={},
    keywords='data_utility',
    )
# #}
# change setup_kwds below before the next pkglts tag

# setup_kwds['setup_requires'] = ['openalea.deploy']
# setup_kwds['share_dirs'] = {'share': 'share'}
# setup_kwds['entry_points']["wralea"] = ["openalea.flow control = openalea.core.system", ]
# setup_kwds['entry_points']["console_scripts"] = ["alea = openalea.core.alea:main"]
# setup_kwds['entry_points']['openalea.core'] = [
#             'openalea.core/openalea = openalea.core.plugin.builtin',
#         ]

# do not change things below
# {# pkglts, pysetup.call
setup(**setup_kwds)
# #}