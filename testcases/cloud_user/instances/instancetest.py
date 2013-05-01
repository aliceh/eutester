#!/usr/bin/env python
#
#
# Description:  This script encompasses test cases/modules concerning instance specific behavior and
#               features for Eucalyptus.  The test cases/modules that are executed can be 
#               found in the script under the "tests" list.

import time
from concurrent.futures import ThreadPoolExecutor
import threading
from eucaops import Eucaops
from eutester.eutestcase import EutesterTestCase
from eucaops import EC2ops
import os
import re
import random


class InstanceBasics(EutesterTestCase):
    def __init__(self, extra_args= None):
        self.setuptestcase()
        self.setup_parser()
        if extra_args:
            for arg in extra_args:
                self.parser.add_argument(arg)
        self.parser.add_argument("--user-data")
        self.get_args()
        # Setup basic eutester object
        if self.args.region:
            self.tester = EC2ops( credpath=self.args.credpath, region=self.args.region)
        else:
            self.tester = Eucaops(config_file=self.args.config, password=self.args.password, credpath=self.args.credpath)
        self.tester.poll_count = 120

        ### Add and authorize a group for the instance
        self.group = self.tester.add_group(group_name="group-" + str(time.time()))
        self.tester.authorize_group_by_name(group_name=self.group.name )
        self.tester.authorize_group_by_name(group_name=self.group.name, port=-1, protocol="icmp" )
        ### Generate a keypair for the instance
        self.keypair = self.tester.add_keypair( "keypair-" + str(time.time()))
        self.keypath = '%s/%s.pem' % (os.curdir, self.keypair.name)
        self.image = self.args.emi
        if not self.image:
            self.image = self.tester.get_emi(root_device_type="instance-store")
        self.address = None
        self.volume = None
        self.private_addressing = False
        zones = self.tester.ec2.get_all_zones()
        self.zone = random.choice(zones).name
        self.reservation = None
        self.reservation_lock = threading.Lock()

    def set_reservation(self, reservation):
        self.reservation_lock.acquire()
        self.reservation = reservation
        self.reservation_lock.release()

    def clean_method(self):
        self.tester.cleanup_artifacts()

    def BasicInstanceChecks(self, zone = None):
        """
        This case was developed to run through a series of basic instance tests.
             The tests are as follows:
                   - execute run_instances command
                   - make sure that public DNS name and private IP aren't the same
                       (This is for Managed/Managed-NOVLAN networking modes)
                   - test to see if instance is ping-able
                   - test to make sure that instance is accessible via ssh
                       (ssh into instance and run basic ls command)
             If any of these tests fail, the test case will error out, logging the results.
        """
        if zone is None:
            zone = self.zone
        reservation = self.tester.run_instance(self.image, user_data=self.args.user_data, username=self.args.instance_user, keypair=self.keypair.name, group=self.group.name, zone=zone)
        for instance in reservation.instances:
            self.assertTrue( self.tester.wait_for_reservation(reservation) ,'Instance did not go to running')
            self.assertTrue( self.tester.ping(instance.public_dns_name), 'Could not ping instance')
            self.assertFalse( instance.found("ls -1 /dev/" + instance.rootfs_device + "2",  "No such file or directory"),  'Did not find ephemeral storage at ' + instance.rootfs_device + "2")
        self.set_reservation(reservation)
        return reservation

    def ElasticIps(self, zone = None):
        """
       This case was developed to test elastic IPs in Eucalyptus. This test case does
       not test instances that are launched using private-addressing option.
       The test case executes the following tests:
           - allocates an IP, associates the IP to the instance, then pings the instance.
           - disassociates the allocated IP, then pings the instance.
           - releases the allocated IP address
       If any of the tests fail, the test case will error out, logging the results.
        """
        if zone is None:
            zone = self.zone
        if not self.reservation:
            self.reservation = self.tester.run_instance(username=self.args.instance_user, keypair=self.keypair.name, group=self.group.name,zone=zone)
        else:
            reservation = self.reservation

        for instance in reservation.instances:
            if instance.public_dns_name == instance.private_ip_address:
                self.tester.debug("WARNING: System or Static mode detected, skipping ElasticIps")
                return reservation
            self.address = self.tester.allocate_address()
            self.assertTrue(self.address,'Unable to allocate address')
            self.tester.associate_address(instance, self.address)
            instance.update()
            self.assertTrue( self.tester.ping(instance.public_dns_name), "Could not ping instance with new IP")
            self.tester.disassociate_address_from_instance(instance)
            self.tester.release_address(self.address)
            self.address = None
            instance.update()
            self.assertTrue( self.tester.ping(instance.public_dns_name), "Could not ping after dissassociate")
        self.set_reservation(reservation)
        return reservation

    def MultipleInstances(self, available_small=None,zone = None):
        """
        This case was developed to test the maximum number of m1.small vm types a configured
        cloud can run.  The test runs the maximum number of m1.small vm types allowed, then
        tests to see if all the instances reached a running state.  If there is a failure,
        the test case errors out; logging the results.
        """
        if self.reservation:
            self.tester.terminate_instances(self.reservation)
            self.set_reservation(None)

        if available_small is None:
            available_small = self.tester.get_available_vms()

        if zone is None:
            zone = self.zone
        reservation = self.tester.run_instance(self.image, user_data=self.args.user_data, username=self.args.instance_user,keypair=self.keypair.name, group=self.group.name,min=2, max=2, zone=zone)
        self.assertTrue( self.tester.wait_for_reservation(reservation) ,'Not all instances  went to running')
        self.set_reservation(reservation)
        return reservation

    def LargestInstance(self, zone = None):
        """
        This case was developed to test the maximum number of c1.xlarge vm types a configured
        cloud can run.  The test runs the maximum number of c1.xlarge vm types allowed, then
        tests to see if all the instances reached a running state.  If there is a failure,
        the test case errors out; logging the results.
        """
        if zone is None:
            zone = self.zone
        if self.reservation:
            self.tester.terminate_instances(self.reservation)
            self.set_reservation(None)
        reservation = self.tester.run_instance(self.image, user_data=self.args.user_data, username=self.args.instance_user,keypair=self.keypair.name, group=self.group.name,type="c1.xlarge",zone=zone)
        self.assertTrue( self.tester.wait_for_reservation(reservation) ,'Not all instances  went to running')
        self.set_reservation(reservation)
        return reservation

    def MetaData(self, zone=None):
        """
        This case was developed to test the metadata service of an instance for consistency.
        The following meta-data attributes are tested:
           - public-keys/0/openssh-key
           - security-groups
           - instance-id
           - local-ipv4
           - public-ipv4
           - ami-id
           - ami-launch-index
           - reservation-id
           - placement/availability-zone
           - kernel-id
           - public-hostname
           - local-hostname
           - hostname
           - ramdisk-id
           - instance-type
           - any bad metadata that shouldn't be present.
        Missing nodes
         ['block-device-mapping/',  'ami-manifest-path']
        If any of these tests fail, the test case will error out; logging the results.
        """
        if zone is None:
            zone = self.zone
        if not self.reservation:
            reservation = self.tester.run_instance(self.image, user_data=self.args.user_data, username=self.args.instance_user,keypair=self.keypair.name, group=self.group.name, zone=zone)
        else:
            reservation = self.reservation
        for instance in reservation.instances:
            ## Need to verify  the public key (could just be checking for a string of a certain length)
            self.assertTrue(re.match(instance.get_metadata("public-keys/0/openssh-key")[0].split('eucalyptus.')[-1], self.keypair.name), 'Incorrect public key in metadata')
            self.assertTrue(re.match(instance.get_metadata("security-groups")[0], self.group.name), 'Incorrect security group in metadata')
            # Need to validate block device mapping
            #self.assertTrue(re.search(instance_ssh.get_metadata("block-device-mapping/")[0], "")) 
            self.assertTrue(re.match(instance.get_metadata("instance-id")[0], instance.id), 'Incorrect instance id in metadata')
            self.assertTrue(re.match(instance.get_metadata("local-ipv4")[0] , instance.private_ip_address), 'Incorrect private ip in metadata')
            self.assertTrue(re.match(instance.get_metadata("public-ipv4")[0] , instance.ip_address), 'Incorrect public ip in metadata')
            self.assertTrue(re.match(instance.get_metadata("ami-id")[0], instance.image_id), 'Incorrect ami id in metadata')
            self.assertTrue(re.match(instance.get_metadata("ami-launch-index")[0], instance.ami_launch_index), 'Incorrect launch index in metadata')
            self.assertTrue(re.match(instance.get_metadata("reservation-id")[0], self.reservation.id), 'Incorrect reservation in metadata')
            self.assertTrue(re.match(instance.get_metadata("placement/availability-zone")[0], instance.placement), 'Incorrect availability-zone in metadata')
            self.assertTrue(re.match(instance.get_metadata("kernel-id")[0], instance.kernel),  'Incorrect kernel id in metadata')
            self.assertTrue(re.match(instance.get_metadata("public-hostname")[0], instance.public_dns_name), 'Incorrect public host name in metadata')
            self.assertTrue(re.match(instance.get_metadata("local-hostname")[0], instance.private_dns_name), 'Incorrect private host name in metadata')
            self.assertTrue(re.match(instance.get_metadata("hostname")[0], instance.dns_name), 'Incorrect host name in metadata')
            self.assertTrue(re.match(instance.get_metadata("ramdisk-id")[0], instance.ramdisk ), 'Incorrect ramdisk in metadata') #instance-type
            self.assertTrue(re.match(instance.get_metadata("instance-type")[0], instance.instance_type ), 'Incorrect instance type in metadata')
            BAD_META_DATA_KEYS = ['foobar']
            for key in BAD_META_DATA_KEYS:
                self.assertTrue(re.search("Not Found", "".join(instance.get_metadata(key))), 'No fail message on invalid meta-data node')
        self.set_reservation(reservation)
        return reservation

    def DNSResolveCheck(self, zone=None):
        """
        This case was developed to test DNS resolution information for public/private DNS
        names and IP addresses.  The tested DNS resolution behavior is expected to follow
        AWS EC2.  The following tests are ran using the associated meta-data attributes:
           - check to see if Eucalyptus Dynamic DNS is configured
           - nslookup on hostname; checks to see if it matches local-ipv4
           - nslookup on local-hostname; check to see if it matches local-ipv4
           - nslookup on local-ipv4; check to see if it matches local-hostname
           - nslookup on public-hostname; check to see if it matches local-ipv4
           - nslookup on public-ipv4; check to see if it matches public-host
        If any of these tests fail, the test case will error out; logging the results.
        """
        if zone is None:
            zone = self.zone
        if not self.reservation:
            reservation = self.tester.run_instance(self.image, user_data=self.args.user_data, username=self.args.instance_user,keypair=self.keypair.name, group=self.group.name, zone=zone)
        else:
            reservation = self.reservation
        for instance in reservation.instances:

            # Test to see if Dynamic DNS has been configured # 
            if re.match("internal", instance.private_dns_name.split('eucalyptus.')[-1]):
                # Per AWS standard, resolution should have private hostname or private IP as a valid response
                # Perform DNS resolution against private IP and private DNS name
                # Check to see if nslookup was able to resolve
                self.assertTrue(re.search('answer\:', instance.sys("nslookup " +  instance.get_metadata("hostname")[0])[3]), "DNS lookup failed for hostname.")
                # Since nslookup was able to resolve, now check to see if nslookup on local-hostname returns local-ipv4 address
                self.assertTrue(re.search(instance.get_metadata("local-ipv4")[0], instance.sys("nslookup " + instance.get_metadata("hostname")[0])[5]), "Incorrect DNS resolution for hostname.")
                # Check to see if nslookup was able to resolve
                self.assertTrue(re.search('answer\:', instance.sys("nslookup " +  instance.get_metadata("local-hostname")[0])[3]), "DNS lookup failed for private hostname.")
                # Since nslookup was able to resolve, now check to see if nslookup on local-hostname returns local-ipv4 address
                self.assertTrue(re.search(instance.get_metadata("local-ipv4")[0], instance.sys("nslookup " + instance.get_metadata("local-hostname")[0])[5]), "Incorrect DNS resolution for private hostname.")
                # Check to see if nslookup was able to resolve
                self.assertTrue(re.search('answer\:', instance.sys("nslookup " +  instance.get_metadata("local-ipv4")[0])[3]), "DNS lookup failed for private IP address.")
                # Since nslookup was able to resolve, now check to see if nslookup on local-ipv4 address returns local-hostname
                self.assertTrue(re.search(instance.get_metadata("local-hostname")[0], instance.sys("nslookup " +  instance.get_metadata("local-ipv4")[0])[4]), "Incorrect DNS resolution for private IP address")
                # Perform DNS resolution against public IP and public DNS name
                # Check to see if nslookup was able to resolve
                self.assertTrue(re.search('answer\:', instance.sys("nslookup " +  instance.get_metadata("public-hostname")[0])[3]), "DNS lookup failed for public-hostname.")
                # Since nslookup was able to resolve, now check to see if nslookup on public-hostname returns local-ipv4 address
                self.assertTrue(re.search(instance.get_metadata("local-ipv4")[0], instance.sys("nslookup " + instance.get_metadata("public-hostname")[0])[5]), "Incorrect DNS resolution for public-hostname.")
                # Check to see if nslookup was able to resolve
                self.assertTrue(re.search('answer\:', instance.sys("nslookup " +  instance.get_metadata("public-ipv4")[0])[3]), "DNS lookup failed for public IP address.")
                # Since nslookup was able to resolve, now check to see if nslookup on public-ipv4 address returns public-hostname
                self.assertTrue(re.search(instance.get_metadata("public-hostname")[0], instance.sys("nslookup " +  instance.get_metadata("public-ipv4")[0])[4]), "Incorrect DNS resolution for public IP address")
        self.set_reservation(reservation)
        return reservation

    def DNSCheck(self, zone=None):
        """
        This case was developed to test to make sure Eucalyptus Dynamic DNS reports correct
        information for public/private IP address and DNS names passed to meta-data service.
        The following tests are ran using the associated meta-data attributes:
           - check to see if Eucalyptus Dynamic DNS is configured
           - check to see if local-ipv4 and local-hostname are not the same
           - check to see if public-ipv4 and public-hostname are not the same
        If any of these tests fail, the test case will error out; logging the results.
        """
        if zone is None:
            zone = self.zone
        if not self.reservation:
            reservation = self.tester.run_instance(self.image, user_data=self.args.user_data, username=self.args.instance_user,keypair=self.keypair.name, group=self.group.name, zone=zone)
        else:
            reservation = self.reservation
        for instance in reservation.instances:
            # Test to see if Dynamic DNS has been configured # 
            if re.match("internal", instance.private_dns_name.split('eucalyptus.')[-1]):
                # Make sure that private_ip_address is not the same as local-hostname
                self.assertFalse(re.match(instance.private_ip_address, instance.private_dns_name), 'local-ipv4 and local-hostname are the same with DNS on')
                # Make sure that ip_address is not the same as public-hostname
                self.assertFalse(re.match(instance.ip_address, instance.public_dns_name), 'public-ipv4 and public-hostname are the same with DNS on')
        self.set_reservation(reservation)
        return reservation

    def Reboot(self, zone=None):
        """
        This case was developed to test IP connectivity and volume attachment after
        instance reboot.  The following tests are done for this test case:
                   - creates a 1 gig EBS volume, then attach volume
                   - reboot instance
                   - attempts to connect to instance via ssh
                   - checks to see if EBS volume is attached
                   - detaches volume
                   - deletes volume
        If any of these tests fail, the test case will error out; logging the results.
        """
        if zone is None:
            zone = self.zone
        if not self.reservation:
            reservation = self.tester.run_instance(self.image, user_data=self.args.user_data, username=self.args.instance_user, keypair=self.keypair.name, group=self.group.name, zone=zone)
        else:
            reservation = self.reservation
        for instance in reservation.instances:
            ### Create 1GB volume in first AZ
            volume = self.tester.create_volume(instance.placement, 1)
            volume_device = instance.attach_volume(volume)
            ### Reboot instance
            instance.reboot_instance_and_verify(waitconnect=20)
            instance.detach_euvolume(volume)
            self.tester.delete_volume(volume)
        self.set_reservation(reservation)
        return reservation

    def Churn(self):
        """
        This case was developed to test robustness of Eucalyptus by starting instances,
        stopping them before they are running, and increase the time to terminate on each
        iteration.  This test case leverages the BasicInstanceChecks test case. The
        following steps are ran:
            - runs BasicInstanceChecks test case 5 times, 10 second apart.
            - While each test is running, run and terminate instances with a 10sec sleep in between.
            - When a test finishes, rerun BasicInstanceChecks test case.
        If any of these tests fail, the test case will error out; logging the results.
        """
        if self.reservation:
            self.tester.terminate_instances(self.reservation)
            self.set_reservation(None)

        available_instances_before = self.tester.get_available_vms(zone=self.zone)

        ## Run through count iterations of test
        count = available_instances_before
        future_instances =[]

        with ThreadPoolExecutor(max_workers=count) as executor:
            ## Start asynchronous activity
            ## Run 5 basic instance check instances 10s apart
            for i in xrange(count):
                future_instances.append(executor.submit(self.BasicInstanceChecks))
                self.tester.sleep(10)

        with ThreadPoolExecutor(max_workers=count) as executor:
            ## Start asynchronous activity
            ## Terminate all instances
            for future in future_instances:
                executor.submit(self.tester.terminate_instances,future.result())

        def available_after_greater():
            return self.tester.get_available_vms(zone=self.zone) >= available_instances_before
        self.tester.wait_for_result(available_after_greater, result=True, timeout=360)

    def PrivateIPAddressing(self, zone = None):
        """
        This case was developed to test instances that are launched with private-addressing
        set to True.  The tests executed are as follows:
            - run an instance with private-addressing set to True
            - allocate/associate/disassociate/release an Elastic IP to that instance
            - check to see if the instance went back to private addressing
        If any of these tests fail, the test case will error out; logging the results.
        """
        if zone is None:
            zone = self.zone
        if self.reservation:
            for instance in self.reservation.instances:
                if instance.public_dns_name == instance.private_ip_address:
                    self.tester.debug("WARNING: System or Static mode detected, skipping PrivateIPAddressing")
                    return self.reservation
            self.tester.terminate_instances(self.reservation)
            self.set_reservation(None)
        reservation = self.tester.run_instance(username=self.args.instance_user, keypair=self.keypair.name, group=self.group.name, private_addressing=True, zone=zone)
        for instance in reservation.instances:
            address = self.tester.allocate_address()
            self.assertTrue(address,'Unable to allocate address')
            self.tester.associate_address(instance, address)
            self.tester.sleep(30)
            instance.update()
            self.assertTrue( self.tester.ping(instance.public_dns_name), "Could not ping instance with new IP")
            address.disassociate()
            self.tester.sleep(30)
            instance.update()
            self.assertFalse( self.tester.ping(instance.public_dns_name), "Was able to ping instance that should have only had a private IP")
            address.release()
            if instance.public_dns_name != instance.private_dns_name:
                self.fail("Instance received a new public IP: " + instance.public_dns_name)
        self.set_reservation(None)
        return reservation

    def ReuseAddresses(self, zone = None):
        """
        This case was developed to test when you run instances in a series, and make sure
        they get the same address.  The test launches an instance, checks the IP information,
        then terminates the instance. This test is launched 5 times in a row.  If there
        is an error, the test case will error out; logging the results.
        """
        prev_address = None
        if zone is None:
            zone = self.zone
            ### Run the test 5 times in a row
        if self.reservation:
            self.tester.terminate_instances(self.reservation)
            self.set_reservation(None)
        for i in xrange(5):
            reservation = self.tester.run_instance(username=self.args.instance_user, keypair=self.keypair.name, group=self.group.name, zone=zone)
            for instance in reservation.instances:
                if prev_address is not None:
                    self.assertTrue(re.search(str(prev_address) ,str(instance.public_dns_name)), str(prev_address) +" Address did not get reused but rather  " + str(instance.public_dns_name))
                prev_address = instance.public_dns_name
            self.tester.terminate_instances(reservation)

if __name__ == "__main__":
    testcase = InstanceBasics()
    ### Either use the list of tests passed from config/command line to determine what subset of tests to run
    list = testcase.args.tests or [ "BasicInstanceChecks",  "Reboot", "MetaData", "ElasticIps", "MultipleInstances" , "LargestInstance",
                                   "PrivateIPAddressing", "Churn"]
    ### Convert test suite methods to EutesterUnitTest objects
    unit_list = [ ]
    for test in list:
        unit_list.append( testcase.create_testunit_by_name(test) )
    ### Run the EutesterUnitTest objects

    result = testcase.run_test_case_list(unit_list,clean_on_exit=True)
    exit(result)


