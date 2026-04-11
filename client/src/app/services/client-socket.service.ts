import { Injectable } from '@angular/core';
import { environment } from 'src/environments/environment';
import { io, Socket } from 'socket.io-client';

const ROLE_ATC = 1;

@Injectable({
    providedIn: 'root',
})
export class ClientSocketService {
    socket: Socket;
    constructor() {
        this.connect();
    }

    isSocketAlive() {
        return this.socket && this.socket.connected;
    }

    connect() {
        if (!this.isSocketAlive()) {
            const url = `${environment.serverUrl}`;
            this.socket = io(url, {
                auth: { r: ROLE_ATC },
                transports: ['websocket'],
            });
        }
    }

    off<T>(event: string, action: (data: T) => void): void {
        this.socket.off(event, action);
    }

    getSocketId() {
        return this.socket.id ?? '';
    }

    disconnect() {
        this.socket.disconnect();
    }

    stopListen() {
        this.socket.off();
    }

    listen<T>(event: string, action: (data: T) => void): void {
        this.socket.on(event, action);
    }

    send<T>(event: string, data?: T, callback?: () => void): void {
        this.socket.emit(event, ...[data, callback].filter((x) => x));
    }
}
