from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()
long_description = (here / "README.md").read_text(encoding="utf-8")

setup(
    name="alarmy-cli",
    version="1.0.2",
    packages=find_packages(),
    install_requires=[],
    entry_points={
        'console_scripts': [
            'alarm-clock=alarm_clock.cli:main',
        ],
    },
    author="Ramanshu Gawande",
    description="A thread-safe, persistent, dual-mode CLI Alarm Clock",
    long_description=long_description,
    long_description_content_type="text/markdown",
    python_requires='>=3.8',
)
