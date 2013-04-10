# -*- coding: utf-8 -*-

from setuptools import setup

__version__ = '0.9.0'

setup(
    name = 'console',
    license='MIT',
    version = __version__,
    description = 'A Python port of Symfony2 Console Component.',
    author = 'Sébastien Eustace',
    author_email = 'sebastien.eustace@gmail.com',
    url = 'https://github.com/SDisPater/console-component',
    packages = ['console'],
    install_requires = [],
    tests_require=['nose'],
    test_suite='nose.collector',
    classifiers = [
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)