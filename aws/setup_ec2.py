"""Configures an EC2 instance for running Memrise."""

import logging
import os.path as opath
import sys
import traceback as tb
import socket
import itertools as itt
import os
import runcmd
import tempfile as tempf

logging.basicConfig(level=logging.INFO)

log = logging.getLogger("setup_ec2")

INSTALL_PACKAGES = ["build-essential",
                    "curl", 
                    "cmake", 
                    "emacs", 
                    "git-core",
                    "gfortran",
                    "libblas-dev",
                    "libatlas3gf-base",
                    "ipython",
                    "libaio-dev",
                    "libncurses5-dev",
                    "lsof",
                    "htop",
                    "mercurial",
                    "nginx",
                    "apache2",
                    "libapache2-mod-wsgi",
                    "lvm2",
                    "memcached",
                    "mdadm",
                    "apachetop",
                    "python-dev", 
                    "python-setuptools",
                    "screen", 
                    "sqlite3", 
                    "subversion",
                    "tmux",
                    "unzip",
                    "vim-nox",
                    "sysstat",
                    "zip",
                    "mailutils",
                    "postfix",
                    "libsasl2-2",
                    "python-boto",
                    ]

INSTALL_PYTHON_PACKAGES = ["pip",
                           "virtualenv",
                           "argparse"]

def create_memrise_user():
    runcmd.check_sudo(["groupadd", "memrise"])
    runcmd.check_sudo(["useradd", "-g", "memrise", "-G", "admin", "-s", "/bin/bash", "-m", "memrise"])

    runcmd.install_dirs(["~memrise/log", 
                  "~memrise/memrise",],
                 owner="memrise",
                 group="memrise", 
                 mode="0700")

    runcmd.create_ssh_key("memrise")

def generate_root_ssh_key():
    runcmd.create_ssh_key("root")

def upgrade_install_packages():
    runcmd.apt_get(["update"])
    runcmd.apt_get(["upgrade"])
    runcmd.apt_get(["install"] + INSTALL_PACKAGES)
    runcmd.check_sudo(["easy_install"] + INSTALL_PYTHON_PACKAGES)

def configure_ssh():
    runcmd.install_files("/etc/ssh", ["sshd_config"])
    runcmd.restart_service("ssh")

def install_mysql():
    log.info("Downloading MySQL 5.5.19 Source")
    runcmd.run(["wget", "-O", "mysql-5.5.19.tar.gz",
                "http://dev.mysql.com/get/Downloads/MySQL-5.5/mysql-5.5.19.tar.gz/from/http://mysql.he.net/"])

    log.info("Unpacking MySQL 5.5.19 Source")
    runcmd.run(["tar", "xzf", "mysql-5.5.19.tar.gz"])

    log.info("Configuring MySQL 5.5.19 Source")
    runcmd.run(["cmake", "."], cwd="mysql-5.5.19")

    log.info("Building MySQL 5.5.19 Source")
    runcmd.run(["make", "-j", "4"], cwd="mysql-5.5.19")

    log.info("Installing MySQL 5.5.19 Source to /usr/local/mysql")
    runcmd.check_sudo(["make" ,"install"], cwd="mysql-5.5.19")

    runcmd.install_files("/etc/profile.d", ["mysql.sh"])
    runcmd.install_files("/etc/ld.so.conf.d", ["mysql-ld.so.conf"])
    runcmd.check_sudo(['ldconfig'])


def configure_postfix(host_name):
    main_cf = open(runcmd.rsrc_path("main.cf.in")).read() % locals()
    open(runcmd.rsrc_path("main.cf"), "w").write(main_cf)

    main_cf = open(runcmd.rsrc_path("virtual.in")).read() % locals()
    open(runcmd.rsrc_path("virtual"), "w").write(main_cf)

    runcmd.install_files("/etc/postfix", [runcmd.rsrc_path(f) for f in ["main.cf", "sasl_passwd", "virtual"]])
    runcmd.install_files("/etc", [runcmd.rsrc_path("aliases")])
    runcmd.check_sudo(["postmap", "/etc/postfix/sasl_passwd"])
    runcmd.check_sudo(["postmap", "/etc/postfix/virtual"])
    runcmd.check_sudo(["newaliases"])
    runcmd.restart_service("postfix")

raid_phys_devs = [("/dev/sd%s" % d) for d in ("hijk")]
def configure_db_raid():
    p = raid_phys_devs[::2]
    n = raid_phys_devs[1::2]

    log.info("Creating RAID0 arrays")
    raid_devs = []
    for i, (a, b) in itt.izip(itt.count(20), itt.izip(p, n)):
        r = "/dev/md%d" % i
        runcmd.check_sudo(["mdadm", "--create", "--level=0", "--raid-devices=2", r, a, b])
        raid_devs.append(r)

    log.info("Creating RAID1 array")
    runcmd.check_sudo(["mdadm", "--create", "--force", "--level=1", "--raid-devices=%d" % len(raid_devs),
                "/dev/md0"] + raid_devs)

    log.info("Creating MySQL Logical Volume")
    runcmd.check_sudo(["pvcreate", "/dev/md0"])
    runcmd.check_sudo(["vgcreate", "mysql", "/dev/md0"])
    runcmd.check_sudo(["lvcreate", "-nmysql", "-l75%FREE", "mysql"])
    runcmd.check_sudo(["mkfs.ext4", "/dev/mysql/mysql"])

    with open("/etc/fstab") as fstab_in:
        with open(runcmd.rsrc_path("fstab"), "w") as fstab_out:
            fstab_out.write(fstab_in.read())
            fstab_out.write("\n")
            fstab_out.write("\t".join(("/dev/mysql/mysql", "/mysql", "ext4", "nodev,nosuid", "0", "0")))
            fstab_out.write("\n")

    runcmd.install_files("/etc", ["fstab"])
    create_mysql_user_fs()

def create_mysql_user_fs():
    runcmd.check_sudo(["mkdir", "/mysql"])
    runcmd.check_sudo(["mount", "/mysql"])

    runcmd.check_sudo(["mkdir", "-p", "/mysql/log", "/mysql/binlog", "/mysql/data"])
    runcmd.check_sudo(["groupadd", "mysql"])
    runcmd.check_sudo(["useradd", "-g", "mysql", "-G", "admin", "-s", "/bin/bash", "-d", "/mysql", "mysql"])
    runcmd.check_sudo(["chown", "-R", "mysql:mysql", "/mysql"])

def mysql_install_db():
    runcmd.run_as_user(["/usr/local/mysql/scripts/mysql_install_db", 
                 "--basedir=/usr/local/mysql", 
                 "--datadir=/mysql/data"],
                user="mysql")
    runcmd.start_service("mysql5.5")

def mysql_secure_db():
    with open(runcmd.rsrc_path("mysql_securedb.sql.in")) as sql_in:
        with open(runcmd.rsrc_path("mysql_secure_db.sql"), "w") as sql_out:
            sql_out.write(sql_in.read())

    with open(runcmd.rsrc_path("mysql_secure_db.sql")) as sql_cmd:
        runcmd.run(["/usr/local/mysql/bin/mysql", "--user=root", "--batch"], 
                   stdin=sql_cmd)

def set_host_name(host_name):
    log.info("Setting host name in /etc/hosts to %s", host_name)

    with open("/etc/hosts") as hosts_in:
        with open(runcmd.rsrc_path("hosts"), "w") as hosts_out:
            hosts_out.write(hosts_in.read())
            hosts_out.write("\n127.0.1.2\t%(host_name)s.memrise.com %(host_name)s\n" % locals())

    runcmd.install_files("/etc", [runcmd.rsrc_path("hosts")])

    with open(runcmd.rsrc_path("hostname"), "w") as hn:
        hn.write("%s\n" % host_name)

    runcmd.install_files("/etc", [runcmd.rsrc_path("hostname")])

    runcmd.check_sudo(["hostname", host_name])

def all_hosts(host_name):
    set_host_name(host_name)
    generate_root_ssh_key()
    create_memrise_user()
    upgrade_install_packages()
    configure_ssh()
    configure_postfix(host_name)
    install_mysql()

def mysql_server():
    install_my_cnf(55)
    configure_db_raid()
    mysql_install_db()
    mysql_secure_db()

def install_my_cnf(buffer_pool_size_gb):
    with open("my.cnf.in") as my_cnf_in:
        with open("my.cnf", "w") as my_cnf_out:
            my_cnf_out.write(my_cnf_in.read() % locals())

    runcmd.install_files("/etc/init", ["mysql5.5.conf"])
    runcmd.install_dirs(["/etc/mysql"])
    runcmd.install_files("/etc/mysql", ["my.cnf"])

def default_server():
    pass

def rabbitmq_server():
    runcmd.apt_get(["install", "rabbitmq-server"])
    runcmd.check_sudo(["rabbitmqctl", "add_user", "memrise", "ktbyunvfy"])
    runcmd.check_sudo(["rabbitmqctl", "add_vhost", "/memrise"])
    runcmd.check_sudo(["rabbitmqctl", "set_permissions", "-p", "/memrise", "memrise", "", ".*", ".*"])
    runcmd.check_sudo(["rabbitmqctl", "delete_user", "guest"])

def jenkins_server():
    runcmd.run(["wget", "-O", "jenkins-ci.org.key", "http://pkg.jenkins-ci.org/debian/jenkins-ci.org.key"])
    runcmd.check_sudo(["apt-key", "add", "jenkins-ci.org.key"])
    runcmd.install_files("/etc/apt/sources.list.d", ["jenkins.list"])
    runcmd.apt_get(["update"])
    runcmd.apt_get(["install", "openjdk-6-jdk", "jenkins", "libcobertura-java"])
    runcmd.install_files("/etc/default", ["jenkins"])

def staging_server():
    runcmd.install_files("/etc/init", ["mysql5.5.conf"])

    with open("/etc/fstab") as fstab_in:
        with open("fstab", "w") as fstab_out:
            for l in fstab_in:
                fstab_out.write(l.replace("/mnt", "/mysql"))

    runcmd.install_files("/etc", ["fstab"])

    runcmd.check_sudo(["umount", "/mnt"])

    create_mysql_user_fs()
    install_my_cnf(1)
    mysql_install_db()
    mysql_secure_db()


host_type_map = {"mysql": mysql_server,
                 "web": default_server,
                 "celery": default_server,
                 "rabbitmq": rabbitmq_server,
                 "jenkins": jenkins_server,
                 "backupdb": staging_server,
                 "staging": staging_server}

if __name__ == "__main__":
    host_type = sys.argv[1]
    host_name = sys.argv[2]

    log.info("Setting up host type %s with host name %s", host_type, host_name)

    host_type = host_type_map[host_type]

    all_hosts(host_name)
    host_type()
