from setuptools import setup, find_packages

setup(
    name="circlepy",  
    version="0.3.62", 
    author="Waleed Salah Aldin",
    author_email="waleed9salah@gmail.com",
    description="Circle.so API made easy with async support for efficient Python integration.",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/atomimus/CirclePy",
    packages=find_packages(), 
    include_package_data=True,
    install_requires=[
        "requests", 
        "aiohttp",
        "pillow",
        "commonmark"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
)
