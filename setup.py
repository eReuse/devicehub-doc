from setuptools import setup, find_packages

setup(
    name='DeviceHub-Doc',
    version='0.1',
    packages=find_packages(),
    url='https://github.com/eReuse/devicehub-doc',
    license='AGPLv3 License',
    author='eReuse team',
    author_email='x.bustamante@ereuse.org',
    description='A small utility to generate class diagrams from the resources of DeviceHub',
    install_requires=[
        'graphviz'
    ],
    include_package_data=True
)
