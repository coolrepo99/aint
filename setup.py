from setuptools import setup, find_packages

setup(
    name = "aint",
    version = "0.1",
    packages = find_packages(),
    install_requires = ["boto >= 2.3.0"],
    entry_points = {
        'console_scripts': [
            'start_instance = aint.start_instance:main',
            "setup_web_ami = aint.setup_web_ami:main",
            "sync_web_dns = aint.setup_web_ami:sync_web_dns",
        ],
    }
)
