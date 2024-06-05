from setuptools import setup, find_packages

setup(
    name="tipi-backend",
    version="1.0.0",
    description="TIPI Backend",
    url="https://github.com/politicalwatch/tipi-backend",
    author="pr3ssh",
    packages=find_packages(),
    install_requires=[
        "flask",
        "flask-restx",
    ],
)
