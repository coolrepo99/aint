import sys
import socket
import subprocess as subp
import traceback as tb
import os.path as opath
import os
import logging

log = logging.getLogger("runcmd")

HOSTNAME = socket.gethostname()

rsrc_path = lambda rsrc: opath.join(opath.dirname(__file__), rsrc)

def create_ssh_key(user):
    key_path = opath.expanduser("~%s/.ssh/id_rsa" % user)
    log.info("Creating SSH key for user %s", user)
    cmd = ["-u", user, "-H", "/bin/bash", "-c", "cd ~ && ssh-keygen -t rsa -b 2048 -N '' -f %(key_path)s" % locals()]
    check_sudo(cmd)
    log.info("SSH RSA Public Key for %s:", user)
    check_sudo(["-u", user, "-H", "cat", key_path + ".pub"])


def restart_service(service):
    log.info("Restarting service: %s", service)

    return check_sudo(["service", service, "restart"])


def start_service(service):
    log.info("Starting service: %s", service)

    return check_sudo(["service", service, "start"])

def stop_service(service):
    log.info("Stopping service: %s", service)

    return check_sudo(["service", service, "stop"])

def disable_service(service):
    stop_service(service)
    log.info("Disabling service %s", service)
    check_sudo(["update-rc.d", service, "stop", "20", "2", "3", "4", "5", "."])

def install_dirs(dirs, owner="root", group="root", mode="0755"):
    log.info("Creating directories %s", dirs)

    cmd = ["install", "-o", owner, "-g", group, "-m", mode, "-d"] + [opath.expanduser(d) for d in dirs]
    return check_sudo(cmd)


def install_files(target, files, owner="root", group="root", mode="0644"):
    log.info("Installing files %s to %s", files, target)

    files = [rsrc_path(f) for f in files]
    cmd = ["install", "-o", owner, "-g", group, "-m", mode] + list(files) + [target]
    return check_sudo(cmd)


def apt_get(args):
    env = dict(os.environ)
    env["DEBIAN_FRONTEND"] = "noninteractive"

    cmd = ["/bin/sh", "-c",
           " ".join(["DEBIAN_FRONTEND=noninteractive apt-get --yes"] + ["'%s'" % a.replace("'", "\'") for a in args])]
    return check_sudo(cmd)


def run_as_user(cmd, user, path=None, **kwargs):
    if path is None:
        path = "~%s" % user

    path = opath.expanduser(path)
    cmd = ["-u", user, "-H"] + list(cmd)

    return check_sudo(cmd, cwd=path, **kwargs)


def check_sudo(cmd, *args, **kwargs):
    cmd = ["sudo"] + list(cmd)

    run(cmd, *args, **kwargs)

def run(cmd, *args, **kwargs):
    try:
        subp.check_call(cmd, *args, **kwargs)
    except subp.CalledProcessError, e:
        log.error("Command %s failed with status: %d", cmd, e.returncode)
        raise
    except:
        log.error("Command %s failed with exception:", cmd)
        log.error(tb.format_exc())
        raise

def wait(func):
    """Calls `cond` in an exponential-backoff loop until it returns `True`."""

    for i in itt.count(0):
        if func():
            break

        if i > 5:
            i = 5

        time.sleep(0.25 * (2**i))
