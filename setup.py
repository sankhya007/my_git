from setuptools import setup, find_packages

setup(
    name="mygit",
    version="0.1.0",
    description="A minimal Git implementation in Python",
    packages=find_packages(),
    package_dir={'': '.'},
    python_requires=">=3.7",
    entry_points={
        'console_scripts': [
            'mygit=src.cli:main',
        ],
    },
    # Include package data if needed
    include_package_data=True,
    zip_safe=False,
)