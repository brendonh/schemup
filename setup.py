from setuptools import setup, find_packages

setup(name="schemup",
      version="0.1",

      description="Database-agnostic schema upgrade tools",
      author="Brendon Hogger",
      author_email="brendonh@cogini.com",
      url="https://github.com/brendonh/schemup",
      long_description=open('README.md').read(),

      download_url="https://github.com/brendonh/schemup/zipball/master",

      packages = find_packages(),
      zip_safe = False,

      install_requires = [
      ],

      package_data = {
      },

)
