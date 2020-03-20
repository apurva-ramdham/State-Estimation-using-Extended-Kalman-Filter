#!/usr/bin/env python

# Columbia Engineering
# MECS 4602 - Fall 2018

import math
import numpy
import time

import rospy

from state_estimator.msg import RobotPose
from state_estimator.msg import SensorData

class Estimator(object):
    def __init__(self):

        # Publisher to publish state estimate
        self.pub_est = rospy.Publisher("/robot_pose_estimate", RobotPose, queue_size=1)

        # Initial estimates for the state and the covariance matrix
        self.x = numpy.zeros((3,1))
        self.P = numpy.zeros((3,3))

        # Covariance matrix for process (model) noise
        self.V = numpy.zeros((3,3))
        self.V[0,0] = 0.0025
        self.V[1,1] = 0.0025
        self.V[2,2] = 0.005

        self.step_size = 0.01

        # Subscribe to command input and sensory output of robot
        rospy.Subscriber("/sensor_data", SensorData, self.sensor_callback)
        
    # This function gets called every time the robot publishes its control 
    # input and sensory output. You must make use of what you know about 
    # extended Kalman filters to come up with an estimate of the current
    # state of the robot and covariance matrix.
    # The SensorData message contains fields 'vel_trans' and 'vel_ang' for
    # the commanded translational and rotational velocity respectively. 
    # Furthermore, it contains a list 'readings' of the landmarks thein
    # robot can currently observe
    def estimate(self, sens):
	x_hat= numpy.zeros((3,1))
	F = numpy.eye(3)
	P_hat= numpy.zeros((3,1))
        x = numpy.zeros((3,1))
	P = numpy.zeros((3,1))
	a= 0
	reading = []
        x_hat[0] = self.x[0]+self.step_size*sens.vel_trans*math.cos(self.x[2])
	x_hat[1] = self.x[1]+self.step_size*sens.vel_trans*math.sin(self.x[2])
	x_hat[2] = self.x[2]+self.step_size*sens.vel_ang
	F[0][2] = -self.step_size*sens.vel_trans*math.sin(self.x[2])
	F[1][2] = self.step_size*sens.vel_trans*math.cos(self.x[2])
	F_T = numpy.transpose(F)
	P_hat = numpy.add(numpy.dot(F,numpy.dot(self.P,F_T)),self.V)
	length = len(sens.readings)
	if length > 0:
	    for i in range(length):
		if math.sqrt((x_hat[0]-sens.readings[i].landmark.x)*(x_hat[0]-sens.readings[i].landmark.x)+(x_hat[1]-sens.readings[i].landmark.y)*(x_hat[1]-sens.readings[i].landmark.y))>0.1:
		    reading.append(sens.readings[i])
		    a=a+1
		else:
		    continue
	if a == 0:
	    x = x_hat
	    P= P_hat
	else:
            H = numpy.zeros((a*2,3))
            W = numpy.zeros((a*2,a*2))
            R = numpy.zeros((3,a*2))
            nu = numpy.zeros((2*a,1))
	    y= numpy.zeros((2*a,1))
	    H_x = numpy.zeros((2*a,1))
	    for i in range(a):
	     xr=x_hat[0]
             yr=x_hat[1]
             thr=x_hat[2]
             xl=reading[i].landmark.x
             yl=reading[i].landmark.y
             dx=xr-xl
             dy=yr-yl
             e=1/(1+(dy**2/dx**2))
             c=(-e*dy/dx**2)
             d=e/dx
             H[2*i]=(x_hat[0]-reading[i].landmark.x)/math.sqrt((x_hat[0]-reading[i].landmark.x)*(x_hat[0]-reading[i].landmark.x)+(x_hat[1]-reading[i].landmark.y)*(x_hat[1]-reading[i].landmark.y))
             H[2*i,1]=(x_hat[1]-reading[i].landmark.y)/math.sqrt((x_hat[0]-reading[i].landmark.x)*(x_hat[0]-reading[i].landmark.x)+(x_hat[1]-reading[i].landmark.y)*(x_hat[1]-reading[i].landmark.y))
             H[2*i,2]=0
             H[2*i+1]=c
             H[2*i+1,1]=d
             H[2*i+1,2]=-1
             W[2*i][2*i] = 0.1
	     W[2*i+1][2*i+1] = 0.05
             y[2*i] = reading[i].range
	     y[2*i+1] = reading[i].bearing
	     H_x[2*i] = math.sqrt((x_hat[0]-reading[i].landmark.x)*(x_hat[0]-reading[i].landmark.x)+(x_hat[1]-reading[i].landmark.y)*(x_hat[1]-reading[i].landmark.y))
	     H_x[2*i+1] = math.atan2(reading[i].landmark.y-x_hat[1], reading[i].landmark.x-x_hat[0])-x_hat[2]
	   
	  
	    S = numpy.add(numpy.dot(H,numpy.dot(P_hat,numpy.transpose(H))),W)
	    R = numpy.dot(P_hat,numpy.dot(numpy.transpose(H),numpy.linalg.inv(S)))
            nu =numpy.subtract(y,H_x)
	    for i in range(a):
             if nu[2*i+1] < -math.pi:
                nu[2*i+1] = nu[2*i+1]+(2*math.pi)
             elif nu[2*i+1] > math.pi:
                nu[2*i+1] =nu[2*i+1]- 2*math.pi
	    x = numpy.add(x_hat,numpy.dot(R,nu))
	    P = numpy.subtract(P_hat,numpy.dot(R,numpy.dot(H,P_hat)))


	self.x = x
	self.P = P
	
	
    def sensor_callback(self,sens):

        # Publish state estimate 
        self.estimate(sens)
        est_msg = RobotPose()
        est_msg.header.stamp = sens.header.stamp
        est_msg.pose.x = self.x[0]
        est_msg.pose.y = self.x[1]
        est_msg.pose.theta = self.x[2]
        self.pub_est.publish(est_msg)

if __name__ == '__main__':
    rospy.init_node('state_estimator', anonymous=True)
    est = Estimator()
    rospy.spin()
