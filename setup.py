from setuptools import setup, find_packages


requires = [
    "six==1.15.0",
    "PyYAML==5.4.1",
    "psycopg2-binary==2.8.6"
]


setup(
    name="schemup",
    version="1.0",
    description="Database-agnostic schema upgrade tools",
    long_description=open('README.md').read(),
    author="Brendon Hogger",
    author_email="brendonh@gmail.com",
    url="https://github.com/brendonh/schemup",
    scripts=[],
    packages=find_packages(),
    install_requires=requires,
    package_data={},
    include_package_data=False,
    license="Apache License 2.0",
    python_requires=">= 2.7",
    classifiers=[]
)
