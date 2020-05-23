from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name = "lrtools",
    description = "Retrieve photos informations from lightroom catalog",
    long_description = long_description,
    long_description_content_type = "text/markdown",
    url = "https://github.com/fdenivac/Lightroom-SQL-tools",
    version = "1.0.0",
    author = "fedor denivac",
    author_email = "fdenivac@gmail.com",
    license = "GNU GPLv3",
    keywords = "lightroom sql photo",
    classifiers = [
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.7",
        "Environment :: Console",
        "Topic :: Software Development :: Libraries",
        "Topic :: Multimedia :: Graphics",
    ],
    python_requires='>=3.7',
    package_dir={'lrtools': 'lrtools'},
    packages=['lrtools'],
    scripts = ['lrtools.ini', 'lrselect.py', 'lrsmart.py' ],
)