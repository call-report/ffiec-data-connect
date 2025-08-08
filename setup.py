from setuptools import setup, find_packages

from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name='ffiec-data-connect',
    python_requires='>3.9.0',
    version='0.3.0',
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
          'zeep',
          'xmltodict',
          'requests',
          'pandas',
          'defusedxml>=0.7.1',  # Security: XXE prevention
          'typing-extensions>=4.0.0;python_version<"3.10"',  # Typing support
      ],
    extras_require={
        'async': [
            'aiohttp>=3.8.0',
            'asyncio-throttle>=1.0.0',
        ],
        'dev': [
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
            'pytest-asyncio>=0.20.0',
            'mypy>=1.0.0',
        ],
    },

)