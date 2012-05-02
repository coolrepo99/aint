# maps the instance size to the machine image we want to use
# (32 vs 64 bit) (since the smaller instance sizes have to be 32-bit)
ami_32bit = "ami-ab36fbc2" # 32-bit, $0.17/hour, 4 cores, 1.7.GB
ami_64bit = "ami-ad36fbc4" # 64-bit, $0.34/hour, 2 cores, 7.5GB
instance_ami_map = {
    "m1.xlarge": ami_64bit,
    "m2.4xlarge": ami_64bit,
    "m1.large": ami_64bit,
    "c1.medium": ami_32bit,
    "m1.small": ami_32bit,
    }

INSTANCE_TYPES = {
    'DEFAULT': "m1.large",
    'WEB': 'c1.medium',
    'DATABASE': "m2.4xlarge",
    'STAGING': 'm1.large',
    'RABBITMQ': "m1.small",
    'JENKINS': "m1.small",
    }
