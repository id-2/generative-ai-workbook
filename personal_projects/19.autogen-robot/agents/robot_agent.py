
"""
Agent wrapper class for intefacing with the Autogen
using the RobotMotionManager to interface with the raspberry
pi robot. 

Written by: Aaron Ward - 3rd December 2023
"""
import os
import sys
import autogen
import logging

from robot.managers.robot_motion_manager import RobotMotionManager
from agents.agent_base import AgentBase

from autogen.agentchat.contrib.gpt_assistant_agent import GPTAssistantAgent

sys.path.append("../")

class RobotAgent(AgentBase):
    """
    Agent wrapper class for intefacing with the Autogen/chroma and Chainlit.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.model = kwargs.get('model', "gpt-4-1106-preview")
        self.robot_motion_manager = RobotMotionManager(model=self.model)

        self.instantiate_two_way_chat()

    def get_system_messages(self):
        """
        Get system messages for different agent roles.
        Returns:
            dict: A dictionary of system messages.
        """
        system_messages = {
            "ROBOT_ASSISTANT_SYSTEM_MESSAGE": (
                """
                You are a Raspberry pi humanoid robot, your role involves understanding instructions and executing actions through the robot. 

                When you receive a command, follow these steps:
                1. Identify the User's Intent: Understand the command and its context. The intent might involve moving the robot, manipulating objects, or gathering information.
                2. Execute Commands: Use predefined functions to translate these instructions into actions. For example, `move_forward()`, `pick_object()`, or `scan_area()`.

                Key Points to Remember:
                - Utilize Context: If the command relates to previous actions or instructions, take that into account to make informed decisions.
                - Tools: You send the action name to `send_action()` function. The following capabilities to you right now are "kneel_down" and "t-pose"
                    You only pick from these two options, don't pass anything else to `send_action()`
                
                End your process with `TERMINATE` when no further instructions are given, to indicate that the task is complete.
                """
            )
        }

        return system_messages

    def get_function_map(self):
        """
        Updated function map to use RobotMotionManager's methods.
        """
        function_map = {
            "send_action": self.robot_motion_manager.send_action,
        }
        return function_map

    def instantiate_two_way_chat(self):
        logging.info("Initializing Agents")
        system_messages = self.get_system_messages()

        send_action_tool_config = {
            "name": "send_action",
            "description": "Function to send an action group name to command the raspberry pi robot",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                },
                "required": ["command"]
            }
        }

        llm_config = {
            "config_list": self.config_list,
            "assistant_id": None,
            "tools": [
                {
                    "type": "function",
                    "function": send_action_tool_config
                },
            ],
            "model": "gpt-4-1106-preview"
        }

        sql_assistant = GPTAssistantAgent(
            name="Robot_Motion_Assistant",
            instructions=system_messages['ROBOT_ASSISTANT_SYSTEM_MESSAGE'],
            llm_config=llm_config
        )

        sql_assistant.register_function(
            function_map=self.get_function_map()
        )

        user_proxy = autogen.UserProxyAgent(
            name="user_proxy",
            is_termination_msg=lambda msg: "TERMINATE" in msg["content"],
            code_execution_config=False,
            human_input_mode="NEVER",
            max_consecutive_auto_reply=3,
        )

        self.user_proxy = user_proxy
        self.secondary_agent = sql_assistant

    def stuff_context(self, prompt):
        # Context stuffing
        termination_notice = self.get_additional_termination_notice()

        # Convert to string if 'text' attribute is not found
        prompt_text = prompt.text if hasattr(prompt, 'text') else str(prompt)
        prompt = prompt_text + f"\n\n{termination_notice}"

        return prompt

    def run(self, prompt):
        """Initiate a chat"""
        # prompt = self.stuff_context(prompt)

        if not self.user_proxy or not self.secondary_agent:
            raise ValueError(
                f"Error occurred initiating the agents {self.user_proxy}, {self.secondary_agent}")
        self.user_proxy.initiate_chat(
            self.secondary_agent, message=prompt, clear_history=False, config_list=self.config_list)

    def _continue(self, prompt):
        """Continue previous chat"""
        # prompt = self.stuff_context(prompt)

        if not self.user_proxy or not self.secondary_agent:
            raise ValueError(
                f"Error occurred initiating the agents {self.user_proxy}, {self.secondary_agent}")
        self.user_proxy.send(recipient=self.secondary_agent, message=prompt)