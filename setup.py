#!/usr/bin/env python
# coding=utf8

from setuptools import setup

setup(
    name='CCentral',
    version='0.2.0',
    description='CCentral client library',
    author='Santtu Järvi',
    author_email='santtu.jarvi@finfur.net',
    url='https://github.com/slvwolf/python-ccentral',
    packages=['ccentral'],
    requires=["etcd"],
    install_requires=["python-etcd>=0.4.3"],
    classifiers=["Programming Language :: Python :: 2.7"]
)