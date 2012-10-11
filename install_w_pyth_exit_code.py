#!/usr/bin/python
#This code prepares eutester environment and outputs install log info and exit code info into two files.
#Writing of the log info and exit code info is executed through python (not shell) calls

import sys
import subprocess


def pcmd(cmd):


    comstr = '\nCOMMAND :' + cmd + '\n'
    print comstr
    p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
    output = p.stdout.read()
    retcode = str(p.wait())
    f.write(comstr + output)
    f1.write(comstr+ 'Exitcode: '+retcode )
subprocess.call('rm -f install_log.txt', shell=True)
subprocess.call('rm -f install_exit_code.txt', shell=True)

workmain = "/root/" #main working directory
#output = open("eutester_output.txt", "w")
#error = open("eutester_error.txt", "w")
f = open("install_log.txt", "w")
f1 = open("install_exit_code.txt", "w")
while (sys.version_info < (2, 6)):
    print "Found python version "+str(sys.version_info[0])+"."+str(sys.version_info[1])+ " must use python 2.6 or greater."
    sys.exit()


def main():

    cmd="cd "+ workmain + " ;" +" yum -y install python-setuptools"
    pcmd(cmd)

    cmd="cd "+ workmain +";"+" easy_install virtualenv"
    pcmd(cmd)

    cmd="cd "+ workmain +";"+" virtualenv virtual_env"
    pcmd(cmd)

    cmd="bash -c 'cd "+ workmain +"virtual_env/bin; source activate'"
    #; echo exit code $?; echo prompt $PS1 '"
    pcmd(cmd)


    cmd="cd "+ workmain +";"+" wget http://argparse.googlecode.com/files/argparse-1.2.1.tar.gz -O argparse.tar.gz && tar -zxvf argparse.tar.gz"
    pcmd(cmd)

    cmd="cd "+ workmain +"argparse-1.2.1 ; python setup.py install"
    pcmd(cmd)

    cmd="cd "+ workmain +";"+" easy_install boto==2.5.2"
    pcmd(cmd)

    cmd="cd "+ workmain +";"+" yum -y install git gcc python-paramiko python-devel"
    pcmd(cmd)

    cmd="cd "+ workmain +";"+" git clone https://github.com/eucalyptus/eutester.git"
    pcmd(cmd)

    cmd="cd " + workmain +"eutester ; git checkout testing"
    pcmd(cmd)

    cmd="cd " + workmain +"eutester ; python ./setup.py install"
    pcmd(cmd)

    cmd="cd "+ workmain +";"+" mkdir testerworkdir"
    pcmd(cmd)

    cmd="cd "+ workmain +";"+" yum -y install ntp"
    pcmd(cmd)

    cmd="chkconfig ntpd on ; service ntpd start && ntpdate -u 0.centos.pool.ntp.org"
    pcmd(cmd)

    # to extract ntp server address from ntp.conf file:  
    # cat /etc/ntp.conf|grep "server 0.*pool.ntp.org" |awk '{print $2}'

    cmd="ntpdate -u 0.centos.pool.ntp.org"
    pcmd(cmd)

    f.close()
    f1.close()

if __name__ == '__main__':
    main()
