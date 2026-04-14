# Legacy class! unsupported Ingescape integration (might be a future angle of work)

# import ingescape as igs  
# from app.utils.constants import REQUEST_OUTPUTS, ACTION_OUTPUTS
# import sys

# class Echo:
#     def __init__(self):
#         self._requests = {name: False for name in REQUEST_OUTPUTS}
#         self._actions = {name: False for name in ACTION_OUTPUTS}
#         self.positions = {} #! lon, lat, speed, head; final_pos would be nice
#         self._register_callbacks()

#     ## PRIVATE ##

#     def _register_callbacks(self):
#         igs.observe_agent_events(Echo.on_agent_event_callback, self)
#         igs.observe_freeze(Echo._on_freeze_callback, self)
#         igs.observe_input("reset", Echo._reset_callback, self)

#     ## CALLBACKS ##
#     @staticmethod
#     def on_agent_event_callback(event, uuid, name, event_data, my_data):
#         agent_object = my_data
#         assert isinstance(agent_object, Echo)
#         print(f"[Agent Event] {event} from {name} ({uuid}) → {event_data}")

#     @staticmethod
#     def _on_freeze_callback(my_data):
#         assert isinstance(my_data, Echo)
#         print(f"[Freeze] Agent frozen.")

#     @staticmethod
#     def _reset_callback(my_data):
#         assert isinstance(my_data, Echo)
#         print(f"[Reset] Reset triggered")
#         my_data.reset()

#     def _set_output(self, pool, name, value):
#         if name not in pool:
#             raise AttributeError(f"Unknown output '{name}'")
#         pool[name] = value
#         igs.output_set_bool(name, value)

#     ## PUBLIC ##
#     def set_request(self, name: str, value: bool):
#         self._set_output(self._requests, name, value)

#     def set_action(self, name: str, value: bool):
#         self._set_output(self._actions, name, value)

#     def reset(self):
#         for name in self._requests:
#             self.set_request(name, False)
#         for name in self._actions:
#             self.set_action(name, False)

#     def disconnect(self):
#         self.reset()
#         # igs.stop() #! Not here

#     #! static for now
#     @staticmethod
#     def define_inputs_outputs():
#         igs.input_create("reset", igs.IMPULSION_T, None)
#         for name in REQUEST_OUTPUTS:
#             igs.output_create(name, igs.BOOL_T, None)
#         for name in ACTION_OUTPUTS:
#             igs.output_create(name, igs.BOOL_T, None)

#     @staticmethod
#     def start_ingescape_agent(device: str = "wlp0s20f3", port: int = 5670):
#         igs.agent_set_name("CPDLC-GROUND")
#         igs.definition_set_version("1.0")
#         igs.log_set_console(True)
#         igs.log_set_file(True, None)
#         igs.log_set_stream(True)
#         igs.set_command_line(sys.executable + " " + " ".join(sys.argv))
#         igs.log_set_console_level(igs.LOG_INFO)
#         Echo.define_inputs_outputs()
#         igs.start_with_device(device, port)
#         print(f"[Ingescape] Agent started on {device}:{port}")
