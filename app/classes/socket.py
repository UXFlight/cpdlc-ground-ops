from flask_socketio import SocketIO, join_room, leave_room
from typing import Optional, Any

class SocketService:
    def __init__(self, socketio, metrics: Optional[Any] = None): 
        self.socketio : SocketIO = socketio
        self.metrics = metrics

    def listen(self, event_name, callback):
        self.socketio.on(event_name)(callback)

    def send(self, event, data, room=None): 
        self.socketio.emit(event, data, to=room)
        if self.metrics:
            self.metrics.record_emit(event, room)

    def enter_room(self, sid, room):
        join_room(room, sid=sid)

    def leave_room(self, sid, room):
        leave_room(room, sid=sid)

    # security helper
    def disconnect(self, sid: str):
        self.socketio.disconnect(sid)