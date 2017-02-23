from setuptools import setup

setup(name='cfpecker',
      version='0.1',
      description='Automated modpack builder utility',
      url='https://github.com/NikkyAI/cfpecker',
      author='NikkyAi',
      author_email='root@nikky.moe',
      license='LGPL',
      packages=['cfpecker'],
      install_requires=[
          'appdirs',
          'requests',
          'pyaml',
          'rfc6266',
          'lepl',
          'beautifulsoup4',
          'pyhocon',
          'mavenpy'
      ],
      entry_points={
        'console_scripts': [
            'cfpecker=cfpecker.command_line:main',
        ],
      },
      zip_safe=False)
