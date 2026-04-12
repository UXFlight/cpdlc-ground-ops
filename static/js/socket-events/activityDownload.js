const { jsPDF } = window.jspdf;
import { dashboardState } from "../state/settingsState.js";

export const handleActivityDownload = (data) => {
  const rawLogs = Array.isArray(data?.logs) ? data.logs : [];
  const pilotId = dashboardState.sid;
  const generatedAt = new Date();

  const LOG_START_REGEX = /(?=\[\d{2}:\d{2}:\d{2}\])/g;
  const LOG_PARSE_REGEX = /^\[(\d{2}:\d{2}:\d{2})\]\s+([A-Z]+)\s+(.*)$/;

  const normalizeLogs = (logs) => {
    return logs
      .flatMap((entry) => String(entry).split(LOG_START_REGEX))
      .map((entry) => entry.trim())
      .filter(Boolean);
  };

  const parseLogs = (logs) => {
    return normalizeLogs(logs).map((line) => {
      const match = line.match(LOG_PARSE_REGEX);

      if (!match) {
        return {
          time: '--:--:--',
          type: 'LOG',
          message: line,
        };
      }

      const [, time, type, message] = match;

      return {
        time,
        type,
        message: message.trim(),
      };
    });
  };

  const formatDateTime = (date) => {
    const pad = (n) => String(n).padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
  };

  const buildFileName = () => {
    const safePilotId = String(pilotId).replace(/[^a-zA-Z0-9_-]/g, '_');
    const stamp = formatDateTime(generatedAt).replace(/[: ]/g, '-');
    return `pilot-activity-${safePilotId}-${stamp}.pdf`;
  };

  const parsedLogs = parseLogs(rawLogs);

  const doc = new jsPDF({
    orientation: 'p',
    unit: 'mm',
    format: 'a4',
  });

  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();

  const marginLeft = 14;
  const marginRight = 14;
  const marginTop = 14;
  const marginBottom = 14;

  const timeColWidth = 24;
  const typeColWidth = 24;
  const gutter = 4;
  const messageX = marginLeft + timeColWidth + typeColWidth + gutter;
  const messageWidth = pageWidth - marginRight - messageX;

  let y = marginTop;

  const drawMainHeader = () => {
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(18);
    doc.text('Pilot Activity Report', marginLeft, y);

    y += 8;

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(10);
    doc.text(`Pilot ID: ${pilotId}`, marginLeft, y);
    y += 5;
    doc.text(`Generated: ${formatDateTime(generatedAt)}`, marginLeft, y);
    y += 5;
    doc.text(`Entries: ${parsedLogs.length}`, marginLeft, y);
    y += 7;

    doc.setDrawColor(210);
    doc.setLineWidth(0.4);
    doc.line(marginLeft, y, pageWidth - marginRight, y);
    y += 8;
  };

  const drawPageHeader = () => {
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(11);
    doc.text('Pilot Activity Report', marginLeft, marginTop);

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(9);
    doc.text(`Pilot ID: ${pilotId}`, pageWidth - marginRight, marginTop, { align: 'right' });

    doc.setDrawColor(225);
    doc.setLineWidth(0.3);
    doc.line(marginLeft, marginTop + 3, pageWidth - marginRight, marginTop + 3);

    y = marginTop + 9;
  };

  const drawFooter = (pageNumber, totalPages) => {
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(8);
    doc.setTextColor(120);
    doc.text(
      `Page ${pageNumber} / ${totalPages}`,
      pageWidth - marginRight,
      pageHeight - 6,
      { align: 'right' }
    );
    doc.setTextColor(0);
  };

  const ensureSpace = (neededHeight) => {
    if (y + neededHeight <= pageHeight - marginBottom) return;

    doc.addPage();
    drawPageHeader();
  };

  const drawLogBlock = (log, index) => {
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(9.5);
    const messageLines = doc.splitTextToSize(log.message, messageWidth);
    const textHeight = Math.max(5, messageLines.length * 4.2);
    const blockHeight = Math.max(8, textHeight + 2);

    ensureSpace(blockHeight + (index > 0 ? 2 : 0));

    if (index > 0) {
      doc.setDrawColor(238);
      doc.setLineWidth(0.25);
      doc.line(marginLeft, y - 1.5, pageWidth - marginRight, y - 1.5);
    }

    doc.setFont('courier', 'bold');
    doc.setFontSize(9);
    doc.text(log.time, marginLeft, y + 4);

    doc.setFont('helvetica', 'bold');
    doc.setFontSize(9);
    doc.text(log.type, marginLeft + timeColWidth, y + 4);

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(9.5);
    doc.text(messageLines, messageX, y + 4);

    y += blockHeight;
  };

  drawMainHeader();

  if (parsedLogs.length === 0) {
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(11);
    doc.text('No activity logs available.', marginLeft, y);
  } else {
    parsedLogs.forEach((log, index) => drawLogBlock(log, index));
  }

  const totalPages = doc.getNumberOfPages();

  for (let page = 1; page <= totalPages; page += 1) {
    doc.setPage(page);
    drawFooter(page, totalPages);
  }

  doc.save(buildFileName());
};