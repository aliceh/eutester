#!/usr/bin/python


import sys
import subprocess

def pcmd(cmd):
    print  '\nCOMMAND :' + cmd + '\n'
    subprocess.call('echo "COMMAND: ' + cmd + '" >>/root/eutester_install.log;', shell=True)
    output = subprocess.call( cmd +'; echo "Exit code" $? >> /root/eutester_install.log;', shell=True)
    #    os.system(cmd)

subprocess.call('rm -f eutester_install.log', shell=True)

workmain = "/root/" #main working directory

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



if __name__ == '__main__':
    main()



