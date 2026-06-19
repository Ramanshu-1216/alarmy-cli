from setuptools import setup, find_packages

setup(
    name="alarm-clock",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[],
    entry_points={
        'console_scripts': [
            'alarm-clock=alarm_clock.cli:main',
        ],
    },
    author="Senior Software Engineer candidate",
    description="A thread-safe, persistent, dual-mode CLI Alarm Clock",
    python_requires='>=3.8',
)
