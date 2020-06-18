from setuptools import setup, find_packages
from codecs import open
from os import path



here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'clairmeta/info.py')) as f:
    exec(f.read())

with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()


setup(
    name='clairmeta',
    version=__version__,

    description='Digital Cinema Package (DCP) probing and checking utility',
    long_description=long_description,
    url='https://github.com/Ymagis/ClairMeta',

    author=__author__,
    author_email='support.sol@ymagis.com',

    license=__license__,

    classifiers=[
        'Development Status :: 5 - Production/Stable',

        'Intended Audience :: Developers',
        'Topic :: Utilities',
        'Topic :: Multimedia :: Video',
        'Topic :: Software Development :: Libraries :: Python Modules',

        'License :: OSI Approved :: BSD License',

        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],

    keywords='digital cinema dcp dcdm dsm check probe smpte interop',

    packages=find_packages(exclude=['packaging', 'docs', 'tests']),

    install_requires=[
        'lxml',
        'dicttoxml',
        'xmltodict',
        'python-dateutil',
        'six',
        'pyopenssl',
        'pycountry',
        'shutilwhich',
        'freetype-py'
    ],

    # 2.7 or 3.4+
    python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, <4',

    package_data={
        'clairmeta': ['xsd/*'],
    },
)
