#!/usr/bin/python

"""Sets up the Django site for serving, and Celery for scheduled jobs."""

import logging
import os.path as opath
import sys
import traceback as tb
import socket
import itertools as itt
import os
import runcmd as rc
import subprocess as subp

logging.basicConfig(level=logging.INFO)

log = logging.getLogger("setup_web")

try:
    import settings as settings
except:
    log.error("settings.py must be in the current working directory or on PYTHONPATH.")
    raise

os.environ["PATH"] = opath.pathsep.join((["/usr/local/mysql/bin"] + list(os.environ["PATH"].split(opath.pathsep))))

def checkout_etc():
    with open(rc.rsrc_path("known_hosts")) as known_hosts:
        rc.check_sudo(["/bin/bash", "-c", "cat >> /root/.ssh/known_hosts"], stdin=known_hosts)

    if opath.isdir("/etc/.git"):
        log.warn("/etc .git exists, cowardly skipping creating it")
        return

    log.info("Initializing repository in /etc")
    rc.check_sudo(["git", "init"], cwd="/etc")
    rc.check_sudo(["git", "config", "--global", "user.name", settings.etc_repo_user], cwd="/etc")
    rc.check_sudo(["git", "config", "--global", "user.email", settings.etc_repo_email], cwd="/etc")
    rc.check_sudo(["git", "remote", "add", "origin", settings.etc_repo_uri],
                  cwd="/etc")

    log.info("Fetching /etc repository from %s", settings.etc_repo_uri)
    rc.check_sudo(["git", "fetch"], cwd="/etc")
    rc.check_sudo(["git", "branch", "master", "origin/master"], cwd="/etc")
    rc.check_sudo(["git", "checkout", "-f", "master"], cwd="/etc")

    rc.restart_service('memcached')
    
    # because you need to do extra stuff to get apache2 working (see setup_amazon.txt)
    rc.stop_service('apache2')

    log.info("/etc updated from repository")

def enable_site():
    log.info("Enabling web site %s", settings.site_config_name)

    rc.check_sudo(["a2dissite", "000-default"])
    rc.check_sudo(["a2ensite", settings.site_config_name])
    rc.restart_service("apache2")

    if opath.exists("/etc/nginx/sites-enabled/default"):
        rc.check_sudo(["rm", "nginx/sites-enabled/default"], cwd="/etc")

    rc.check_sudo(["ln", "-sf",
                   "/etc/nginx/sites-available/%s" % settings.site_config_name,
                   "/etc/nginx/sites-enabled/%s" % settings.site_config_name])
    rc.restart_service("nginx")

    log.info("Enabled web site %s", settings.site_config_name)

def checkout_site():
    setup_known_hosts()

    if not opath.exists(opath.expanduser("~/memrise")):
        os.mkdir(opath.expanduser("~/memrise"))

    log.info("Checking out memrise site from unfuddle")

    rc.run(["git", "clone", "git@memrise.unfuddle.com:memrise/memrise-django.git", "memrise"],
           cwd=opath.expanduser("~/memrise"))

def setup_known_hosts():
    log.info("Adding memrise.unfuddle.com and github.com to known_hosts")

    with open(opath.expanduser("~/.ssh/known_hosts"), "a") as akeys_out:
        with open(rc.rsrc_path("known_hosts")) as akeys_in:
            akeys_out.write("\n" + akeys_in.read() + "\n")

def setup_venv():
    rc.run(["pip", "install", "-E", "../venv", "-r", "requirements.txt"], 
           cwd=opath.expanduser("~/memrise/memrise"))
    os.chmod('/home/memrise/memrise/', 0755)
    os.chmod('/home/memrise/', 0755)

def setup_server():
    checkout_etc()
    enable_site()

def setup_site():
    checkout_site()
    setup_venv()

def setup_bashrc():
    with open(rc.rsrc_path("bashrc.in")) as brc_in:
        with open(opath.expanduser("~/.bashrc"), "a") as brc_out:
            brc_out.write("\n")
            brc_out.write(brc_in.read())

def show_ssh_keys():
    for user in ("root", "memrise"):
        key_path = opath.expanduser("~%s/.ssh/id_rsa" % user)
        log.info("SSH RSA Public Key for %s:", user)
        rc.check_sudo(["-u", user, "-H", "cat", key_path + ".pub"])
        print

def copy_to_memrise():
    log.info("Copying setup_ec2 to memrise home")
    src = subp.Popen(["tar", "c", "-C", opath.expanduser("~"), "setup_ec2"], stdout=subp.PIPE)
    tgt = subp.Popen(["sudo", "-u", "memrise", "tar", "x", "-C", opath.expanduser("~memrise")], stdin=src.stdout)

    src_stat = src.wait()
    tgt_stat = tgt.wait()

    if src_stat or tgt_stat:
        raise Exception("Copying setup_ec2 to memrise user failed: src: %d, tgt: %d" % (src_stat, tgt_stat))

def setup_web():
    setup_server()
    copy_to_memrise()
    rc.disable_service("celeryd")

    rc.run_as_user(["python", "setup_web.py", "memrise-web"], user="memrise", path="~memrise/setup_ec2/aws")

def setup_web_as_memrise():
    checkout_site()
    setup_venv()
    setup_bashrc()

def setup_jenkins():
    rc.install_dirs(["~memrise/log/jenkins"], owner="memrise", group="memrise", mode="0750")
    copy_to_memrise()
    rc.run_as_user(["python", "setup_web.py", "memrise-jenkins"], user="memrise", path="~memrise/setup_ec2/aws")
    rc.restart_service("jenkins")

def setup_jenkins_as_memrise():
    setup_known_hosts()
    rc.run(["git", "clone", "git@github.com:Memrise/jenkins.git"], cwd=opath.expanduser("~"))

def setup_celery():
    checkout_etc()

    rc.run_as_user(["python", "setup_web.py", "memrise-web"], user="memrise", path="~memrise/setup_ec2/aws")

command_map = {"keys": show_ssh_keys,
               "server": setup_server,
               "site": setup_site,
               "venv": setup_venv,
               "web": setup_web,
               "celery": setup_celery,
               "memrise-web": setup_web_as_memrise,
               "jenkins": setup_jenkins,
               "memrise-jenkins": setup_jenkins_as_memrise}

if __name__ == "__main__":
    cmd = command_map[sys.argv[1]]
    cmd()
