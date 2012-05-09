import aws.instances as aint
import aws.setup_dns as sdns
import boto

def start_spare_web_servers(count=4):
    """Start `count` spare web servers if we have that many stopped.

    Make sure you've updated your virtualenv beforehand (to
    get the latest version of the 'aws' library), and deploy
    immediately afterwards."""

    count = int(count)

    srvrs = [i for i in instances() if aint.is_web(i) and aint.is_stopped(i)][:count]

    if not srvrs:
        print("WARNING: No spare web servers.")
        return

    print("Starting servers:")
    print("    " + ", ".join((aint.name(srvr) for srvr in srvrs)))

    for srvr in srvrs:
        srvr.start()

    print("Waiting for servers to start.")
    aint.wait(lambda: aint.all_running(ec2(), srvrs))

    print("Updating DNS.")
    r53 = sdns.connect()
    rrs = sdns.current_rrs(r53)

    [sdns.replace_rr(rrs, aint.memrise_hostname(srvr) + ".", "CNAME", [aint.aws_hostname(srvr) + "."])
     for srvr in srvrs]

    rrs.commit()

    print("WARNING: Started %d web servers. Please run deploy." % (len(srvrs)))
    print("Servers:")
    for srvr in srvrs:
        print("\t" + aint.name(srvr))

def load_balance_web_servers():
    """Syncs running and stopped web servers with the load balancer."""

    srvrs = [i for i in instances() if aint.is_running(i) and aint.is_web(i)]

    elb_conn = boto.connect_elb()
    elb = [e for e in elb_conn.get_all_load_balancers() if e.name == u"Cave"][0]

    elb_ids = set(i.id for i in elb.instances)
    srvr_ids = set(i.id for i in srvrs)

    add_servers = list(srvr_ids - elb_ids)
    remove_servers = list(elb_ids - srvr_ids)

    if add_servers:
        print "Adding servers to load balancer:", ", ".join(add_servers)
        elb.register_instances(add_servers)

    if remove_servers:
        print "Removing servers from load balancer:", ", ".join(remove_servers)
        elb.deregister_instances(remove_servers)

def stop_spare_web_servers(count=4):
    """Stop `count` web servers. Will always keep 4 running."""

    global _instances

    count = int(count)

    srvrs = [i for i in instances() if aint.is_web(i) and aint.is_running(i)]
    stop_srvrs = srvrs[-count:]

    if len(srvrs) - len(stop_srvrs) < 4:
        print("WARNING: %d servers running. Not stopping any more." % len(srvrs))
        return

    print("Stopping servers:")
    print("    " + ", ".join((aint.name(srvr) for srvr in stop_srvrs)))

    for srvr in stop_srvrs:
        srvr.stop()

    aint.wait(lambda: aint.all_stopped(ec2(), stop_srvrs))

    # Dump the instances cache so that load_balance_web_servers gets fresh information.
    _instances = None
    load_balance_web_servers()

    local("./fab touch_wsgi")
