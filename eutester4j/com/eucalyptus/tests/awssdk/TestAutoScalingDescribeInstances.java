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

import com.amazonaws.services.autoscaling.model.*;
import com.amazonaws.services.ec2.model.TerminateInstancesRequest;
import org.testng.annotations.Test;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.TimeUnit;

import static com.eucalyptus.tests.awssdk.Eutester4j.*;

/**
 * This application tests launching and describing instances with auto scaling.
 * 
 * This is verification for the story:
 * 
 * https://eucalyptus.atlassian.net/browse/EUCA-4896
 */
public class TestAutoScalingDescribeInstances {
	@SuppressWarnings("unchecked")
	@Test
	public void AutoScalingDescribeInstancesTest() throws Exception {
        testInfo(this.getClass().getSimpleName());
        getCloudInfo();

		// End discovery, start test
		final List<Runnable> cleanupTasks = new ArrayList<Runnable>();
		try {
			// Create launch configuration
            final String launchConfig = NAME_PREFIX + "DescribeTest";
			print("Creating launch configuration: " + launchConfig);
            createLaunchConfig(launchConfig,IMAGE_ID,INSTANCE_TYPE,null,null,null,null,null,null,null,null);
			cleanupTasks.add(new Runnable() {
				@Override
				public void run() {
					print("Deleting launch configuration: " + launchConfig);
                    deleteLaunchConfig(launchConfig);
				}
			});

			// Create scaling group
            final String groupName = NAME_PREFIX + "DescribeTest";
            Integer minSize = 0;
            Integer maxSize = 1;
            Integer desiredCpacity = 1;
            String healthCheckType = "EC2";
            String terminationPolicy = "OldestInstance";
			print("Creating auto scaling group: " + groupName);
            createAutoScalingGroup(groupName,launchConfig, minSize, maxSize, desiredCpacity,AVAILABILITY_ZONE, null,
                    null, healthCheckType, null, null, terminationPolicy);
			cleanupTasks.add(new Runnable() {
				@Override
				public void run() {
					print("Deleting group: " + groupName);
                    deleteAutoScalingGroup(groupName,true);
				}
			});
			cleanupTasks.add(new Runnable() {
				@Override
				public void run() {
					final List<String> instanceIds = (List<String>) getInstancesForGroup(groupName, null, true);
					print("Terminating instances: " + instanceIds);
					ec2.terminateInstances(new TerminateInstancesRequest()
							.withInstanceIds(instanceIds));
				}
			});

			// Wait for instances to launch
			print("Waiting for instance to launch");
			final long startTime = System.currentTimeMillis();
			final long launchTimeout = TimeUnit.MINUTES.toMillis(5);
			boolean launched = false;
			String instanceId = null;
			while (!launched
					&& (System.currentTimeMillis() - startTime) < launchTimeout) {
				Thread.sleep(5000);
				final List<String> instanceIds = (List<String>) getInstancesForGroup(groupName, "running", true);
				launched = instanceIds.size() == 1;
				instanceId = launched ? instanceIds.get(0) : null;
			}
			assertThat(launched,
					"Instance was not launched within the expected timeout");
			assertThat(instanceId != null, "Instance identifier null");
			print("Instance launched in "
					+ (System.currentTimeMillis() - startTime) + "ms");

			// Describe instance and verify details
			final DescribeAutoScalingInstancesResult instancesResult = as
					.describeAutoScalingInstances(new DescribeAutoScalingInstancesRequest()
							.withInstanceIds(instanceId));
			assertThat(instancesResult.getAutoScalingInstances().size() == 1,
					"Auto scaling instance found");
			final AutoScalingInstanceDetails details = instancesResult
					.getAutoScalingInstances().get(0);
			print("Verifying instance details: " + details);
			assertThat(
					instanceId.equals(details.getInstanceId()),
					"Incorrect instance id " + instanceId + " != "
							+ details.getInstanceId());
			assertThat(
                    groupName.equals(details.getAutoScalingGroupName()),
					"Incorrect group name " + groupName + " != "
							+ details.getAutoScalingGroupName());
			assertThat(
                    launchConfig.equals(details.getLaunchConfigurationName()),
					"Incorrect config name " + launchConfig + " != "
							+ details.getLaunchConfigurationName());
			assertThat(
                    AVAILABILITY_ZONE.equals(details.getAvailabilityZone()),
					"Incorrect AZ " + AVAILABILITY_ZONE + " != "
							+ details.getAvailabilityZone());
			assertThat(
					Arrays.asList("Healthy", "Unhealthy").contains(
							details.getHealthStatus()),
					"Invalid health status: " + details.getHealthStatus());
			assertThat(
					Arrays.asList("Pending", "Quarantined", "InService",
							"Terminating", "Terminated").contains(
							details.getLifecycleState()),
					"Invalid lifecycle state: " + details.getLifecycleState());

			// Update group desired capacity and wait for instances to terminate
			print("Setting desired capacity to 0 for group: " + groupName);
			as.setDesiredCapacity(new SetDesiredCapacityRequest()
					.withAutoScalingGroupName(groupName).withDesiredCapacity(0));

			// Wait for instances to terminate
			print("Waiting for instance to terminate");
			final long terminateStartTime = System.currentTimeMillis();
			final long terminateTimeout = TimeUnit.MINUTES.toMillis(5);
			boolean terminated = false;
			while (!terminated
					&& (System.currentTimeMillis() - terminateStartTime) < terminateTimeout) {
				Thread.sleep(5000);
				final List<String> instanceIds = (List<String>) getInstancesForGroup(groupName, null, true);
				terminated = instanceIds.size() == 0;
			}
			assertThat(terminated,
					"Instance was not terminated within the expected timeout");
			print("Instance terminated in "
					+ (System.currentTimeMillis() - terminateStartTime) + "ms");
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
}
