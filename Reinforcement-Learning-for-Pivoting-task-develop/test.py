import time
import gym
import pandas as pd

from PPO.PPO import PPO
import numpy as np
import pivoting_env
import yaml
from utils.utils import rescale_action_space
from utils.utils import DataImputation

# Read YAML file
with open('./parameters.yaml', 'r') as file_descriptor:
    parameters = yaml.load(file_descriptor)


def test(imputer):
    global done
    print("============================================================================================")

    ################## hyperparameters ##################
    env_name = parameters['model']['env_name']
    has_continuous_action_space = True
    max_ep_len = parameters['model']['max_ep_len']  # max timesteps in one episode
    action_std = parameters['ppo']['action_parameters'][
        'min_action_std']  # set same std for action distribution which was used while saving

    render = parameters['test']['render']  # render environment on screen
    frame_delay = 0  # if required; add delay b/w frames

    total_test_episodes = parameters['test']['number_of_test_episodes']  # total num of testing episodes

    K_epochs = parameters['ppo']['hyperparameters']['k_epochs']  # update policy for K epochs
    eps_clip = parameters['ppo']['hyperparameters']['eps_clip']  # clip parameter for PPO
    gamma = parameters['ppo']['hyperparameters']['gamma']  # discount factor

    lr_actor = parameters['agent']['mlp']['lr_actor']  # learning rate for actor
    lr_critic = parameters['agent']['mlp']['lr_critic']  # learning rate for critic

    activate_occlusion = parameters['model']['activate_occlusion']
    failure_rate = parameters['model']['failure_rate']
    log_results = parameters['test']['log_results']
    #####################################################

    env = gym.make(env_name)

    # state space dimension
    state_dim = env.observation_space.shape[0]

    # action space dimension
    if has_continuous_action_space:
        action_dim = len(parameters['model']['ppo_acting_joints'])
    else:
        action_dim = env.action_space.n

    # initialize a PPO agent
    ppo_agent = PPO(state_dim, action_dim, lr_actor, lr_critic, gamma, K_epochs, eps_clip, has_continuous_action_space,
                    action_std)

    # preTrained weights directory

    random_seed = 42  #### set this to load a particular checkpoint trained on random seed
    run_num_pretrained = 0  #### set this to load a particular checkpoint num

    directory = "PPO/PPO_preTrained" + '/' + env_name + '/'
    checkpoint_path = directory + parameters['test']['model_name']
    print("loading network from : " + checkpoint_path)

    ppo_agent.load(checkpoint_path)

    print("--------------------------------------------------------------------------------------------")

    test_running_reward = 0

    if log_results:
        logs = {'episode': [], 'timestep': [], 'action': [], 'state': [], 'reward': [], 'done': [], 'new_state': [],
                'angle_before_act': [], 'angle_after_act': [], 'desired_angle': []} # 'sucess': []
    for ep in range(1, total_test_episodes + 1):
        ep_reward = 0
        state = env.reset()

        for t in range(1, max_ep_len + 1):

            # Occlusion system
            if activate_occlusion:
                trigger_failure = True if (1 - np.random.random()) <= failure_rate else False
                if (imputer.occlusion == True) or (imputer.occlusion == False and trigger_failure):
                    imputer.update_duration()

            #####################
            state[[3]] = state[[3]] * 100
            #####################

            # Append to log file
            if log_results:
                logs['state'].append(state)
                logs['episode'].append(ep)
                logs['timestep'].append(t)
                logs['angle_before_act'].append(env.get_current_angle())
                logs['desired_angle'].append(env.get_desired_angle())

            action = ppo_agent.select_action(state)

            ####!!!!!@#####
            action = rescale_action_space(scale_factor=15, action=action)
            #######

            # Append to log file
            if log_results:
                logs['action'].append(action)

            state, reward, done, _ = env.step(action)
            ep_reward += reward

            # Append to log file
            if log_results:
                aux_state = state.copy()
                aux_state[3] = aux_state[3]*100
                logs['new_state'].append(aux_state)
                logs['reward'].append(reward)
                logs['done'].append(done)
                logs['angle_after_act'].append(env.get_current_angle())
                # logs['sucess'].append(done - env.get_drop_bool())


            if render:
                env.render()
                time.sleep(frame_delay)

            if done:
                break

        # clear buffer
        ppo_agent.buffer.clear()

        print(
            f"Episode : {ep} \t Timestep : {t} \t Average Reward : {int(ep_reward)} "
            f"\t Real : {int(env.get_current_angle())} "
            f"\t Target : {env.get_desired_angle()} \t Sucess : {done - env.get_drop_bool()}")


    env.close()

    # Save log file into a csv
    if log_results:
        logs_df = pd.DataFrame(logs)
        logs_df.to_csv('logs/logs.csv', index=False)

if __name__ == '__main__':
    imputer = DataImputation()
    test(imputer=imputer)
