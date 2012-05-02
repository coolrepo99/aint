from setuptools import setup, find_packages

setup(
    name = "aws",
    version = "0.1",
    packages = find_packages(),
    install_requires = ["dnspython", "boto"],
    entry_points = {
        'console_scripts': [
            'start_instance = aws.start_instance:main',
            "setup_web_ami = aws.setup_web_ami:main",
            "sync_web_dns = aws.setup_web_ami:sync_web_dns",
        ],
    }
)
