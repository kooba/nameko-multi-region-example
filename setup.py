#!/usr/bin/env python
from setuptools import find_packages, setup

setup(
    name='nameko-multi-region-example',
    version='0.0.1',
    description='Shows example of multi region messaging with Nameko',
    packages=find_packages(exclude=['test', 'test.*']),
    install_requires=[
        'nameko==2.4.4',
        'marshmallow==2.9.1'
    ],
    extras_require={
        'dev': [
            'pytest==3.0.3',
            'coverage==4.2',
            'flake8==3.0.4'
        ],
    },
    zip_safe=True
)
