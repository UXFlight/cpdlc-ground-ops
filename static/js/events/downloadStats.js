import { emitActivityRequest } from "../socket/socket-emits.js";

export async function downloadReport() {
    emitActivityRequest();
}
