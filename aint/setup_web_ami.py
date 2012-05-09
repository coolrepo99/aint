"""Sets up web servers from the Memrise Web AMI."""

WEB_AMI = "ami-bdb279d4"
WEB_INSTANCE = "c1.medium"

import logging
import os
import aws.setup_dns as sdns
import aws.runcmd as rc
import aws.instances as aint
import aws.setup_dns as sdns
import re

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("setup_web_ami")

def run_instances(ec2, count, ami=WEB_AMI, instance_type=WEB_INSTANCE):
    """Runs `count` instances using the web AMI."""

    log.info("Requesting %d instances using AMI %s", count, ami)

    res = ec2.run_instances(ami,
                            instance_type=instance_type,
                            placement="us-east-1d",
                            key_name="memrise",
                            min_count=count,
                            max_count=count)

    instances = res.instances
    aint.wait(lambda: aint.all_started(ec2, instances))

    return aint.reservation_instances(ec2, res)

        
web_re = re.compile("web([0-9]+)")
def next_web_server(ec2):
    names = (aint.name(i) for i in aint.walk_instances(ec2) if aint.is_web(i) and not aint.is_terminated(i))

    return sorted(int(web_re.split(n)[1]) for n in names)[-1] + 1

def set_instance_metadata(ec2, instance):
    name = "web%d" % next_web_server(ec2)
    instance.add_tag("instance_type", "web")
    instance.add_tag("Name", name)

def set_instance_dns_name(rrs, instance):
    dns_name = aint.memrise_hostname(instance) + "."
    aws_name = aint.aws_hostname(instance) + "."

    sdns.replace_rr(rrs, dns_name, "CNAME", [aws_name])

def sync_web_dns():
    ec2 = aint.connect()
    r53 = sdns.connect()
    rrs = sdns.current_rrs(r53)

    for instance in (i for i in aint.walk_instances(ec2) 
                     if aint.is_running(i) and aint.is_web(i)):
        print aint.name(instance), aint.aws_hostname(instance)
        set_instance_dns_name(rrs, instance)

    rrs.commit()

def main():
    ec2 = aint.connect()
    r53 = sdns.connect()
    rrs = sdns.current_rrs(r53)
    instances = run_instances(ec2, 4)

    for i in instances:
        set_instance_metadata(ec2, i)
        set_instance_dns_name(rrs, i)

        print i.id, aint.memrise_hostname(i), aint.aws_hostname(i)

    rrs.commit()
