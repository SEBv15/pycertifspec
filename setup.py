from setuptools import setup, find_packages

setup(
    name='pycertifspec',
    version='0.1.1',
    description='Python library for communicating with SPEC and controlling devices',
    author='Sebastian Strempfer',
    author_email='sebastian@strempfer.com',
    url='https://github.com/SEBv15/pycertifspec',
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Natural Language :: English",
        "Topic :: Utilities",
    ],
    platforms=["any"],
    python_requires='>=3.4',
    install_requires=[
        "numpy"
    ]
)
