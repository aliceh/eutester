/*************************************************************************
 * Copyright 2009-2013 Eucalyptus Systems, Inc.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; version 3 of the License.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see http://www.gnu.org/licenses/.
 *
 * Please contact Eucalyptus Systems, Inc., 6755 Hollister Ave., Goleta
 * CA 93117, USA or visit http://www.eucalyptus.com/licenses/ if you need
 * additional information or have any questions.
 ************************************************************************/

package com.eucalyptus.tests.awssdk;

import com.amazonaws.services.autoscaling.model.CreateAutoScalingGroupRequest;
import com.amazonaws.services.autoscaling.model.SetDesiredCapacityRequest;
import com.amazonaws.services.ec2.model.DescribeAvailabilityZonesResult;
import com.amazonaws.services.ec2.model.Instance;
import org.testng.annotations.Test;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.TimeUnit;

import static com.eucalyptus.tests.awssdk.Eutester4j.*;

/**
 * This application tests auto scaling with multiple availability zones.
 * 
 * This is verification for the story:
 * 
 * https://eucalyptus.atlassian.net/browse/EUCA-4992
 */
public class TestAutoScalingMultipleAvailabilityZones {

	@SuppressWarnings("unchecked")
	@Test
	public void AutoScalingMultipleAvailabilityZonesTest() throws Exception {
        testInfo(this.getClass().getSimpleName());
        getCloudInfo();

		// Find an AZ to use
		final DescribeAvailabilityZonesResult azResult = ec2
				.describeAvailabilityZones();

        // If only 1 AZ then do not run test but pass w/ a message
        if (azResult.getAvailabilityZones().size() < 2) {
            print("Test Skipped: Multiple Availability Zones Required");
            return;
        }

		final String availabilityZone1 = azResult.getAvailabilityZones().get(0)
				.getZoneName();
		final String availabilityZone2 = azResult.getAvailabilityZones().get(1)
				.getZoneName();
		print("Using availability zones: "
				+ Arrays.asList(availabilityZone1, availabilityZone2));

		// End discovery, start test
		final String namePrefix = eucaUUID() + "-";
		print("Using resource prefix for test: " + namePrefix);

		final List<Runnable> cleanupTasks = new ArrayList<Runnable>();
		try {
			// Create launch configuration
            final String launchConfig = namePrefix + "MultipleZones";
			print("Creating launch configuration: " +  launchConfig);
            createLaunchConfig(launchConfig,IMAGE_ID,INSTANCE_TYPE,null,null,null,null,null,null,null,null);
			cleanupTasks.add(new Runnable() {
				@Override
				public void run() {
					print("Deleting launch configuration: " + launchConfig);
					deleteLaunchConfig(launchConfig);
				}
			});

			// Create scaling group
			final String groupName = namePrefix + "MultipleZones";
			print("Creating auto scaling group: " + groupName);
			as.createAutoScalingGroup(new CreateAutoScalingGroupRequest()
					.withAutoScalingGroupName(groupName)
					.withLaunchConfigurationName(launchConfig)
					.withDesiredCapacity(2)
					.withMinSize(0)
					.withMaxSize(4)
					.withHealthCheckType("EC2")
					.withAvailabilityZones(availabilityZone1, availabilityZone2)
					.withTerminationPolicies("OldestInstance"));
			cleanupTasks.add(new Runnable() {
				@Override
				public void run() {
					print("Deleting group: " + groupName);
					deleteAutoScalingGroup(groupName, true);
				}
			});

			// Wait for instances to launch
			print("Waiting for 2 instances to launch");
			final long timeout = TimeUnit.MINUTES.toMillis(10);
			List<Instance> instances = (List<Instance>) waitForInstances(timeout, 2, groupName, false);
			assertBalanced(instances, availabilityZone1, availabilityZone2);

			// Update group desired capacity and wait for instances to launch
			print("Setting desired capacity to 4 for group: " + groupName);
			as.setDesiredCapacity(new SetDesiredCapacityRequest()
					.withAutoScalingGroupName(groupName).withDesiredCapacity(4));

			// Wait for instances to launch
			print("Waiting for 2 instances to launch");
			instances = (List<Instance>) waitForInstances(timeout, 4, groupName, false);
			assertBalanced(instances, availabilityZone1, availabilityZone2);

			// Update group desired capacity and wait for instances to launch
			print("Setting desired capacity to 2 for group: " + groupName);
			as.setDesiredCapacity(new SetDesiredCapacityRequest()
					.withAutoScalingGroupName(groupName).withDesiredCapacity(2));

			// Wait for instances to terminate
			print("Waiting for 2 instances to terminate");
			instances = (List<Instance>) waitForInstances(timeout, 2, groupName, false);
			assertBalanced(instances, availabilityZone1, availabilityZone2);

			// Update group desired capacity and wait for instances to terminate
			print("Setting desired capacity to 0 for group: " + groupName);
			as.setDesiredCapacity(new SetDesiredCapacityRequest()
					.withAutoScalingGroupName(groupName).withDesiredCapacity(0));

			// Wait for instances to terminate
			print("Waiting for 2 instances to terminate");
			waitForInstances(timeout, 0, groupName, false);

			// Update group desired capacity and wait for instances to launch
			print("Setting desired capacity to 4 for group: " + groupName);
			as.setDesiredCapacity(new SetDesiredCapacityRequest()
					.withAutoScalingGroupName(groupName).withDesiredCapacity(4));

			// Wait for instances to launch
			print("Waiting for 4 instances to launch");
			instances = (List<Instance>) waitForInstances(timeout, 4,
					groupName, false);
			assertBalanced(instances, availabilityZone1, availabilityZone2);

			print("Test complete");
		} finally {
			// Attempt to clean up anything we created
			Collections.reverse(cleanupTasks);
			for (final Runnable cleanupTask : cleanupTasks) {
				try {
					cleanupTask.run();
				} catch (Exception e) {
					e.printStackTrace();
				}
			}
        }
	}

	private void assertBalanced(final List<Instance> instances,
			final String zone1, final String zone2) {
		final int zone1Count = countZoneInstances(instances, zone1);
		final int zone2Count = countZoneInstances(instances, zone2);

		assertThat(zone1Count + zone2Count == instances.size()
				&& zone1Count == zone2Count, "Zones are not balanced " + zone1
				+ "=" + zone1Count + " / " + zone2 + "=" + zone2Count);
	}

	private int countZoneInstances(final List<Instance> instances,
			final String zone) {
		int count = 0;
		for (final Instance instance : instances) {
			if (instance.getPlacement() != null
					&& zone.equals(instance.getPlacement()
							.getAvailabilityZone())) {
				count++;
			}
		}
		return count;
	}
}
