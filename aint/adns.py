import boto
import itertools as itt
import instances as inst
import ConfigParser as cprs

config = cprs.SafeConfigParser()
config.read("aint.ini")

dns_suffix = config.get("adns", "dns_suffix")
dns_suffix = dns_suffix + "." if dns_suffix[-1] != "." else ""
zone_id = config.get("adns", "zone_id")

def current_rrs(r53, zone_id=zone_id):
    return r53.get_all_rrsets(zone_id)

def get_rrs(rrs, rrname, rrtype=None):
    return (r for r in rrs if r.name==rrname and (r.type==rrtype if rrtype is not None else True))

def create_rr(rrs, rrname, rrtype, rrvalues, rrttl=300):
    rr = rrs.add_change("CREATE", rrname, rrtype, rrttl)
    [rr.add_value(value) for value in rrvalues]

def delete_rr(rrs, rrname, rrtype):
    cur_rrs = get_rrs(rrs, rrname, rrtype)

    for cur_rr in cur_rrs:
        rr = rrs.add_change("DELETE", cur_rr.name, cur_rr.type, cur_rr.ttl)
        [rr.add_value(value) for value in cur_rr.resource_records]

def replace_rr(rrs, rrname, rrtype, rrvalues, rrttl=300):
    delete_rr(rrs, rrname, rrtype)
    create_rr(rrs, rrname, rrtype, rrvalues, rrttl)

def connect():
    return boto.connect_route53()

def sync_instance(rrs, instance):
    """Syncs the DNS CNAME of the instance to the instance. commit()
    must be called on rrs afterwards."""

    replace_rr(rrs, inst.hostname(instance), "CNAME", [inst.aws_hostname(inst)])
