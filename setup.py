# from setuptools import setup
from subzero import setup, Executable

setup(
    name='voodoo',
    version='0.4',
    description='Automated modpack builder utility',
    url='https://github.com/NikkyAI/voodoo-pack',
    author='NikkyAi',
    author_email='root@nikky.moe',
    license='LGPL',
    packages=['voodoo', 'voodoo.provider'],
    install_requires=[
        'appdirs',
        'requests',
        'pyaml',
        'mavenpy',
        'graphviz',
        'jenkinsapi'
    ],
    entry_points={
        'console_scripts': [
            'voodoo=voodoo.voodoo:main',
        ],
    },
    options={
        'build_exe': {
            'hiddenimports': [],
            'pathex': [],
            'datas': [],
        },
        'bdist_msi': {
            'upgrade_code':
            '66620F3A-DC3A-11E2-B341-002219E9B01E',
            # 'shortcuts': [
            #     'ProgramMenuFolder\Hello World = my_project',
            #     # 'ProgramMenuFolder\Hello World\Hello World = my_project',
            # ],
        }
    },
)
