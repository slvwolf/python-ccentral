#!/usr/bin/env python
# coding=utf8
import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="ccentral", # Replace with your own username
    version="0.4.1",
    author='Santtu Järvi',
    author_email='santtu.jarvi@finfur.net',
    description='CCentral client library',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/slvwolf/python-ccentral",
    packages=setuptools.find_packages(),
    install_requires=[
        "pyformance >= 0.4.0",
        "python-etcd == 0.4.5"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: System :: Monitoring",
        "Development Status :: 5 - Production/Stable",
    ],
    python_requires='>=3.6',
)