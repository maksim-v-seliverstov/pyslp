# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name='pyslp',
    version=__import__('pyslp').__version__,
    description='Service Location Protocol, Version 2',
    author='Seliverstov Maksim',
    author_email='Maksim.V.Seliverstov@yandex.ru',
    packages=find_packages(),
    zip_safe=False,
    keywords=['slp', 'openslp', 'slptool', 'slpd', 'service location protocol']
)
