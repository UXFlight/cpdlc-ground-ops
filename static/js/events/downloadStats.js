import { dashboardState } from "../state/settingsState.js";

export async function downloadReport() {
    const pilotId = dashboardState.sid;
    console.log("Downloading report for pilot:", pilotId);
    // const result = await fetch(`${SERVER_URL}/pilot/stats/report/${pilotId}`);
    // const blob = await result.blob();
    // const url = window.URL.createObjectURL(blob);
    //     const a = document.createElement("a");
    //     a.href = url;
    //     a.download = `${pilotId}_report.pdf`;
    //     a.click();
    //     URL.revokeObjectURL(url);
}
