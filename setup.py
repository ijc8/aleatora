import setuptools

# https://packaging.python.org/guides/single-sourcing-package-version/
import codecs
import os.path

def read(rel_path):
    here = os.path.abspath(os.path.dirname(__file__))
    with codecs.open(os.path.join(here, rel_path), 'r') as fp:
        return fp.read()

def get_version(rel_path):
    for line in read(rel_path).splitlines():
        if line.startswith('__version__'):
            delim = '"' if '"' in line else "'"
            return line.split(delim)[1]
    else:
        raise RuntimeError("Unable to find version string.")

version = get_version("src/aleatora/__init__.py")


with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()


setuptools.setup(
    name="aleatora", # Replace with your own username
    version=version,
    author="Ian Clester",
    author_email="ijc@ijc8.me",
    description="Music composition framework based on streams.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ijc8/aleatora",
    project_urls={
        "Bug Tracker": "https://github.com/ijc8/aleatora/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Topic :: Multimedia :: Sound/Audio :: Sound Synthesis",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.6",
    install_requires=[
        "astor",  # TODO: Remove dependency after upgrading to Python >= 3.9, which has ast.unparse().
        "mido",
        "numpy~=1.19.0",
        "oscpy",
        "scipy",
        "sounddevice",
    ],
    extras_require={
        "speech": ["gtts", "streamp3~=0.1.7"],
        # NOTE: This will not work when installing from PyPI, because it's a non-PyPI URL.
        "foxdot": ["FoxDotPatterns @ https://github.com/ijc8/FoxDotPatterns/archive/refs/heads/master.zip"]
    }
)