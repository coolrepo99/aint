import boto
import itertools as itt
import instances as inst

import settings

dns_suffix = settings.dns_suffix + "." if settings.dns_suffix != "." else ""

def current_rrs(r53, zone_id=MEMRISE_ZONE_ID):
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

    memrise_name = ".".join((inst.name(instance), dns_suffix))
    aws_name = inst.aws_hostname(instance) + "."

    replace_rr(rrs, memrise_name, "CNAME", [aws_name])
