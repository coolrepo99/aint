import boto
import itertools as itt
import time

def walk_instances(ec2):
    for res in ec2.get_all_instances():
        for inst in res.instances:
            yield inst

is_terminated = lambda i: i.state == "terminated"
is_running = lambda i: i.state == "running"
is_stopped = lambda i: i.state == "stopped"
is_type = lambda i, t: i.tags.get(u"instance_type") == t
is_web = lambda i: is_type(i, "web")
is_mysql = lambda i: is_type(i, "mysql")
is_celery = lambda i: is_type(i, "celery")
is_staging = lambda i: is_type(i, "staging")
is_rabbitmq = lambda i: is_type(i, "rabbitmq")
is_solr = lambda i: is_type(i, "solr")
is_backupdb = lambda i: is_type(i, "backupdb")

should_deploy = lambda i: is_running(i) and (is_celery(i) or is_web(i) or is_solr(i))
can_batch = lambda i: is_celery(i)

name = lambda i: str(i.tags[u"Name"])

def deployable_instances(ec2):
    for inst in (i for i in walk_instances(ec2) if should_deploy(i)):
        yield inst

aws_hostname = lambda i: str(i.public_dns_name)
memrise_hostname = lambda i: ".".join((name(i), "memrise.com"))
connect = lambda: boto.connect_ec2()

def reservation_instances(ec2, res):
    """Returns the most current instances from a reservation."""

    ress = [r for r in ec2.get_all_instances() if r.id == res.id]
    if not len(ress):
        raise KeyError("Reservation %s not found." % res.id)

    res = ress[0]
    return tuple(i for i in res.instances)

def wait(func):
    """Calls `cond` in an exponential-backoff loop until it returns `True`."""

    for i in itt.count(0):
        if func():
            break

        if i > 5:
            i = 5

        time.sleep(0.25 * (2**i))

def all_status(ec2, instances, status):
    """Returns `True` if all instances are in state `status`."""

    [i.update() for i in instances]

    try:
        return all(i.state==status for i in instances)
    except KeyError:
        return False

def all_running(ec2, instances):
    """Returns `True` if all instances in `res` are running."""

    return all_status(ec2, instances, "running")

def all_stopped(ec2, instances):
    """Returns `True` if all instances in `res` are stopped."""

    return all_status(ec2, instances, "stopped")


ELB_ID = ""
def add_to_elb(elb, instance):
    pass
