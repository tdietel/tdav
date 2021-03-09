import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="tdav-tdietel", # Replace with your own username
    version="0.0.1",
    author="Tom Dietel",
    author_email="tom@dietel.net",
    description="Tiny WebDAV client",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tdietel/tdav",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=[
        'Click', 'jinja2', 'webdavclient3', 'keyring'
    ],
    entry_points={
        'console_scripts': [
            'tdav=tdav:cli',
        ],
    },
)
