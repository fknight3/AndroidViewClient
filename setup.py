#!/usr/bin/env python
import os

from setuptools import setup, find_packages

# Name of the installed package
name = 'androidviewclient3'

# Root of the actual source files
src_root = 'src/com/dtmilano/android'

# Find all (sub)packages in the sources directory
package_names = find_packages(src_root)

# Alias packages as a subpackages/namespace packages of the main package
# https://packaging.python.org/guides/packaging-namespace-packages/
packages = [(name + "." + subpackage) for subpackage in package_names]

# noinspection SpellCheckingInspection
setup(name=name,
      version='15.3.1',
      description=
      '''
      AndroidViewClient3 is a 100% pure python library and tools
      that simplifies test script creation providing higher level
      operations and the ability of obtaining the tree of Views present at
      any given moment on the device or emulator screen.
      ''',
      license='Apache',
      keywords='android uiautomator viewclient monkeyrunner test automation',
      author='Diego Torres Milano, Bojan Potočnik',
      author_email='"Diego Torres Milano" <dtmilano@gmail.com>, "Bojan Potočnik" <info@bojanpotocnik.com>',
      url='https://github.com/bojanpotocnik/AndroidViewClient/',
      packages=[name] + packages,
      namespace_packages=[name] + packages,
      package_dir={
          name: src_root,
          **{name: os.path.join(src_root, name) for name in package_names}
      },
      package_data={name: ['*.png']},
      include_package_data=True,
      scripts=[
          'tools/culebra',
          'tools/dump'
      ],
      classifiers=[
          'Development Status :: 4 - Beta',
          'Intended Audience :: Developers',
          'Natural Language :: English'
          'License :: OSI Approved :: Apache Software License',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7'
      ],
      install_requires=[
          'setuptools',
          'requests',
          'numpy',
          'matplotlib'
      ],
      python_requires='>=3.6'
      )
