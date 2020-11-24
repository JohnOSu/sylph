from setuptools import setup, find_packages

setup(
    name='sylph',
    description='A lightweight python test automation library',

    version='0.6.1',
    author="John O'Sullivan",
    author_email='johnosull9@hotmail.com',
    url='https://www.linkedin.com/in/johnosull9/',

    packages=find_packages(where='src'),
    package_dir={'': 'src'},
)
