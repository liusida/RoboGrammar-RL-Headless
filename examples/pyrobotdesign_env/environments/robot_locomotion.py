import sys, os
base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../')
sys.path.append(base_dir)
sys.path.append(os.path.join(base_dir, 'rl'))
data_dir = os.path.abspath(os.path.join(__file__,"../../../../data/"))
os.environ['ROBOT_DESIGN_DATA_DIR'] = f"{data_dir}/"

import numpy as np
import gym
from gym import utils, spaces
from gym.utils import seeding
from os import path
import copy

from pyrobotdesign_env.simulation.simulation_utils import *
from pyrobotdesign_env.common.common import *
import tasks
import pyrobotdesign
class RobotLocomotionEnv(gym.Env):
    def __init__(self, task="FlatTerrainTask", grammar_file = "grammar_apr30.dot", rule_sequence="0,7,1,13,1,2,16,12,13,6,4,19,4,17,5,3,2,16,4,5,18,9,8,9,9,8"):
        self.render_mode = "off"
        self.rule_sequence = rule_sequence

        # init task and robot
        task_class = getattr(tasks, task)
        self.task = task_class()
        self.robot = build_robot(grammar_file=grammar_file, rule_sequence=rule_sequence)
        
        # get init pos
        self.robot_init_pos, has_self_collision = presimulate(self.robot)
        
        if has_self_collision:
            print_error('robot design has self collision')

        # init simulation
        self.sim = make_sim_fn(self.task, self.robot, self.robot_init_pos)
        self.robot_index = self.sim.find_robot_index(self.robot)

        # init objective function
        self.objective_fn = self.task.get_objective_fn()

        # init frame skip
        self.frame_skip = self.task.interval

        # define action space and observation space
        self.action_dim = self.sim.get_robot_dof_count(self.robot_index)
        self.action_range = np.array([-np.pi, np.pi])
        self.action_space = spaces.Box(low = np.full(self.action_dim, -1.0, dtype=np.float32), 
            high = np.full(self.action_dim, 1.0, dtype=np.float32), dtype = np.float32)

        observation = self.get_obs()
        self.observation_space = spaces.Box(low = np.full(observation.shape, -np.inf, dtype=np.float32), 
            high = np.full(observation.shape, np.inf, dtype=np.float32), dtype = np.float32)

        # init seed
        self.seed()


    def seed(self, seed=None):
        self.np_random, seed = seeding.np_random(seed)
        return [seed]

    def set_frame_skip(self, frame_skip):
        self.frame_skip = frame_skip

    def reset(self):
        self.sim.remove_robot(0)
        self.sim.add_robot(self.robot, self.robot_init_pos, rd.Quaterniond(0.0, 0.0, 1.0, 0.0))
        self.robot_index = self.sim.find_robot_index(self.robot)
        assert self.robot_index == 0
    
        return self.get_obs()

    def get_obs(self):
        state = get_robot_state(self.sim, self.robot_index)
        # obs = deepcopy(state)
        obs = np.hstack((state[0:9], state[10], state[12:])) # remove x, z positions from observation
        return obs

    def compute_reward(self):
        state = get_robot_state(self.sim, self.robot_index)
        base_R = np.reshape(state[0:9], (3, 3))
        base_pos = state[9:12]
        base_vel = state[12:18]

        base_x_axis, target_x_axis = base_R[:, 0], np.array([-1., 0., 0.])
        base_y_axis, target_y_axis = base_R[:, 1], np.array([0., 1., 0.])
        # base_z_axis, target_z_axis = base_R[:, 2], np.array([0., 0., -1.])

        # reward = base_vel[3]
        # reward = base_vel[3] + np.dot(base_x_axis, target_x_axis) * 0.1 + np.dot(base_y_axis, target_y_axis) * 0.1
        reward = base_vel[3] + np.dot(base_x_axis, target_x_axis) * 0.1 + np.dot(base_y_axis, target_y_axis) * 0.1 - np.sum(self.last_u ** 2) / self.action_dim * 0.7
        # reward = 1.0 + base_vel[3] - np.sum(self.last_u ** 2) / self.action_dim * 0.7

        return reward

    def detect_crash(self):
        state = get_robot_state(self.sim, self.robot_index)
        base_R = np.reshape(state[0:9], (3, 3))
        base_pos = state[9:12]
        
        base_x_axis, target_x_axis = base_R[:, 0], np.array([-1., 0., 0.])
        base_y_axis, target_y_axis = base_R[:, 1], np.array([0., 1., 0.])
        base_z_axis, target_z_axis = base_R[:, 2], np.array([0., 0., -1.])
        
        if np.dot(base_x_axis, target_x_axis) < 0. or np.dot(base_y_axis, target_y_axis) < 0. or \
            np.dot(base_z_axis, target_z_axis) < 0.:
            crash = True
        else:
            crash = False

        # crash = False

        return crash

    # control frequency is same as the simulation frequency
    # control observation is directly infered from state
    # control output action is the same as the action in simulation
    def step(self, u):
        u = np.clip(u, -1., 1.)
        
        self.last_u = deepcopy(u)

        action = u * np.pi / 2.

        reward = 0.0
        for _ in range(self.frame_skip):
            self.sim.set_joint_targets(self.robot_index, deepcopy(action.reshape(-1, 1)))
            self.sim.step()
            # reward += self.objective_fn(self.sim)
            reward += self.compute_reward()
            
        obs = self.get_obs()
        
        done = self.detect_crash()
        
        self._render()

        return obs, reward, done, {}
        

    def render(self, mode="human"):
        self.render_mode = mode

    def _render(self):
        if self.render_mode=="human":
            if not hasattr(self, "viewer"):
                self.viewer = rd.GLFWViewer()
            self.viewer.render(self.sim)

    def set_task(self, task):
        # init task and robot
        task_class = getattr(tasks, task)
        self.task = task_class()

    def set_robot(self, grammar_file, rule_sequence):
        self.robot = build_robot(grammar_file, rule_sequence)
        self.rule_sequence = rule_sequence

        # get init pos
        self.robot_init_pos, has_self_collision = presimulate(self.robot)
        
        if has_self_collision:
            print_error('robot design has self collision')

        # init simulation
        self.sim = make_sim_fn(self.task, self.robot, self.robot_init_pos)
        self.robot_index = self.sim.find_robot_index(self.robot)

        # init objective function
        self.objective_fn = self.task.get_objective_fn()

        # init frame skip
        self.frame_skip = self.task.interval

        # define action space and observation space
        self.action_dim = self.sim.get_robot_dof_count(self.robot_index)
        self.action_range = np.array([-np.pi, np.pi])
        self.action_space = spaces.Box(low = np.full(self.action_dim, -1.0, dtype=np.float32), 
            high = np.full(self.action_dim, 1.0, dtype=np.float32), dtype = np.float32)

        observation = self.get_obs()
        self.observation_space = spaces.Box(low = np.full(observation.shape, -np.inf, dtype=np.float32), 
            high = np.full(observation.shape, np.inf, dtype=np.float32), dtype = np.float32)
