from setuptools import setup, find_packages

from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name='ffiec-data-connect',
    python_requires='>3.11.0',
    version='0.4.0',
    license='MIT',
    description="Wrapper for the FFIEC's Webservice API",
    readme='README.md',
    long_description=long_description,
    project_urls={
    'Documentation': 'https://ffiec-data-connect.readthedocs.io/en/latest/',
    'Repo': 'https://github.com/call-report/ffiec-data-connect',
    'Additional Info': 'http://call.report',
    'Author': 'https://mikeh.dev',
},
    long_description_content_type='text/markdown',
    author="Michael Handelman",
    author_email='m@mikeh.dev',
    packages=find_packages('src'),
    include_package_data=True,
    package_dir={'': 'src'},
    url='https://github.com/call-report/ffiec-data-connect',
    keywords='ffiec call report bank regulatory',
    install_requires=[
          'zeep>=4.3.0,<4.4.0',
          'xmltodict>=0.14.0,<0.15.0',
          'requests>=2.32.0',
          'pandas>=2.2.0',
          'polars>=1.29.0'
      ],

)