# from setuptools import setup
from setuptools import setup, find_packages

setup(
    name='voodoo',
    version='0.4',
    description='Automated modpack building utility',
    url='https://github.com/NikkyAI/voodoo-pack',
    author='NikkyAi',
    author_email='root@nikky.moe',
    license='LGPL',
    packages=find_packages(),
    install_requires=[
        'ruamel.yaml<0.15',
        'simplejson',
        'appdirs',
        'requests',
        'jenkinsapi',
        'xmltodict',
        'graphviz',
    ],
    entry_points={
        'console_scripts': [
            'voodoo=voodoo.voodoo:main',
        ],
    }
)
