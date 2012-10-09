#!/usr/bin/python

import os
import subprocess

def pcmd(cmd):
    print  '\nCOMMAND :' + cmd + '\n'
    subprocess.call('echo "COMMAND: ' + cmd + '" >>/root/eutester_install.log;', shell=True)
    output = subprocess.call( cmd +'; echo "Exit code" $? >> /root/eutester_install.log;', shell=True)
    #    os.system(cmd)

subprocess.call('rm -f eutester_install.log', shell=True)

def main():

    cmd="cd /root/ ; yum install python-setuptools"
    pcmd(cmd)

    cmd="cd /root/ ; easy_install virtualenv"
    pcmd(cmd)

    cmd="cd /root/ ;  mkdir virtual_env"
    pcmd(cmd)

    cmd="cd /root/virtual_env ; virtualenv virtual_env"
    pcmd(cmd)

    cmd="cd /root/virtual_env/bin ; source activate"
    pcmd(cmd)

    cmd="cd /root/ ; wget http://argparse.googlecode.com/files/argparse-1.2.1.tar.gz -O argparse.tar.gz && tar -zxvf argparse.tar.gz"
    pcmd(cmd)

    cmd="cd /root/argparse-1.2.1 ; python setup.py install"
    pcmd(cmd)

    cmd="cd /root/ ; easy_install boto==2.5.2"
    pcmd(cmd)

    cmd="cd /root/ ; yum -y install git gcc python-paramiko python-devel"
    pcmd(cmd)

    cmd="cd /root/ ; git clone https://github.com/eucalyptus/eutester.git"
    pcmd(cmd)

    cmd="cd /root/eutester ; git checkout testing"
    pcmd(cmd)

    cmd="cd /root/eutester ; python ./setup.py install"
    pcmd(cmd)

    cmd="cd /root/ ; mkdir testerworkdir"
    pcmd(cmd)

    cmd="cd /root/virtual_env/bin ; source activate"
    pcmd(cmd)


    cmd="cd /root/ ; yum install ntp"
    pcmd(cmd)

    cmd="chkconfig ntpd on ; service ntpd start && ntpdate -u 0.centos.pool.ntp.org"
    pcmd(cmd)

    # to extract ntp server address from ntp.conf file:  
    # cat /etc/ntp.conf|grep "server 0.*pool.ntp.org" |awk '{print $2}'

    cmd="ntpdate -u 0.centos.pool.ntp.org"
    pcmd(cmd)



if __name__ == '__main__':
    main()


