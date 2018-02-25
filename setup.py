#!/usr/bin/env python
# coding=utf8

from setuptools import setup

setup(
    name='CCentral',
    version="0.4.0",
    description='CCentral client library',
    author='Santtu Järvi',
    author_email='santtu.jarvi@finfur.net',
    url='https://github.com/slvwolf/python-ccentral',
    packages=['ccentral'],
    requires=["python-etcd", 'pyformance'],
    install_requires=["python-etcd>=0.4.3", "pyformance"],
    classifiers=["Programming Language :: Python :: 3.5",
                 "Programming Language :: Python :: 3.6"]
)
