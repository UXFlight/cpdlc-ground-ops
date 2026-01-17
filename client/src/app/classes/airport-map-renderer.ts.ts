import { Helipad, ParkingPosition, Runway, Taxiway } from '@app/interfaces/AirMap';
import { ClearanceType, LocationInfo, LonLat, PilotPublicView, StepEvent } from '@app/interfaces/Publics';
import { StepStatus } from '@app/interfaces/StepStatus';
import { AIRPORT_STYLES } from '@app/interfaces/airport-colors';
import { LABELS } from '@app/modules/constants';

export interface MapRenderOptions {
  project: (coord: LonLat) => [number, number];
  showLabels: boolean;
  zoomLevel?: number;
  rotation?: number;
}

export class AirportMapRenderer {
  private planeImage: HTMLImageElement | null = null;
  private planeImageLoaded = false;

  constructor(
    private ctx: CanvasRenderingContext2D,
    private canvas: HTMLCanvasElement
  ) {
    this.setPlaneImage();
  }

  clear(): void {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
  }

  // === Drawers publics ===
  drawRunways(runways: Runway[], options: MapRenderOptions): void {
    this.drawLine(runways, options, AIRPORT_STYLES.runway);
  }

  drawTaxiways(taxiways: Taxiway[], options: MapRenderOptions): void {
    this.drawLine(taxiways, options, AIRPORT_STYLES.taxiway);
  }

  drawHelipads(helipads: Helipad[], options: MapRenderOptions): void {
    this.drawPoint(helipads, options, AIRPORT_STYLES.helipad);
  }

  drawParkings(parkings: ParkingPosition[], options: MapRenderOptions): void {
    this.drawPoint(parkings, options, AIRPORT_STYLES.parking);
  }

  // PILOTS METHODS //
  drawPilots(pilots: PilotPublicView[], options: MapRenderOptions): void {
    for (const pilot of pilots) {
      if (!pilot.plane) continue;
  
      const [x, y] = options.project(pilot.plane.current_pos.coord);
      const heading = pilot.plane.current_heading ?? 0;
      const zoom = options.zoomLevel ?? 1;
      const mapRotation = options.rotation ?? 0;
  
      this.ctx.save();
      this.ctx.translate(x, y);
      this.ctx.rotate(mapRotation + (heading * Math.PI) / 180);
  
      const baseSize = 35;
      const scaleFactor = 1 + (zoom - 1) * 0.2;
      const size = baseSize * scaleFactor;

      if (!this.planeImage || !this.planeImageLoaded) this.setPlaneImage();
      
      const tempCanvas = document.createElement('canvas');
      tempCanvas.width = size;
      tempCanvas.height = size;
      const tempCtx = tempCanvas.getContext('2d')!;
      
      if (this.planeImage) tempCtx.drawImage(this.planeImage, 0, 0, size, size);

      tempCtx.globalCompositeOperation = 'source-in';
      tempCtx.fillStyle = pilot.color || AIRPORT_STYLES.pointFill;
      tempCtx.fillRect(0, 0, size, size);

      this.ctx.drawImage(tempCanvas, -size / 2, -size / 2);
     
      this.ctx.restore();
  
      const activeSteps = this.getActivePilotSteps(pilot);
      if (activeSteps.length > 0) {
        this.drawPilotSteps(pilot.color, activeSteps, x, y);
      }

      if (pilot.renderClearance) this.drawPilotClearances(pilot, options);
    }
  }

  private drawPilotSteps(color : string, activeStep: StepEvent[], x: number, y: number): void {
    if (activeStep.length === 0) return;
  
    const ctx = this.ctx;
    const bubblePaddingX = 6;
    const bubblePaddingY = 4;
    const spacing = 4;
    const fontSize = 12;
  
    ctx.font = `${fontSize}px sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
  
    const renderedSteps = activeStep.map((step: StepEvent) => {
      const label = this.shortenLabelFromStepCode(step.step_code);
      const textWidth = ctx.measureText(label).width;
      const width = textWidth + bubblePaddingX * 2;
      const height = fontSize + bubblePaddingY * 2;
      return { label, width, height };
    });
  
    const totalHeight =
      renderedSteps.reduce((acc, activeStep) => acc + activeStep.height, 0) +
      spacing * (renderedSteps.length - 1);
  
    let currentY = y - totalHeight - 20;
  
    renderedSteps.forEach(({ label, width, height }) => {
      ctx.fillStyle = color ?? '#38bdf8';
      ctx.globalAlpha = 0.85;
      ctx.beginPath();
      ctx.roundRect(x - width / 2, currentY, width, height, 6);
      ctx.fill();
  
      ctx.globalAlpha = 1;
      ctx.fillStyle = '#fff';
      ctx.fillText(label, x, currentY + height / 2);
  
      currentY += height + spacing;
    });
  }

  private drawPilotClearances(pilot: PilotPublicView, options: MapRenderOptions): void {
    const allClearances = Object.values(pilot.clearances)
      .filter(c => c?.instruction?.trim())
      .sort((a, b) => {
        const priority = (type: ClearanceType): number => {
          return type === 'route_change' ? 0 : type === 'taxi' ? 1 : 2;
        };
  
        const pa = priority(a.kind);
        const pb = priority(b.kind);
  
        return pa - pb
      });
  
    const clearance = allClearances[0];
    if (!clearance || !clearance.coords?.length) return;
  
    const color = pilot.color || AIRPORT_STYLES.taxiway;
    const dashed = clearance.kind === 'expected';
  
    const pathCoords = clearance.coords;
    this.drawClearancePath(pathCoords, options, color, dashed);
  
    const finalPos = pilot.plane.final_pos.coord;
    this.drawFinalDestinationMarker(this.ctx, options.project, finalPos, color);
  }
  

  private drawClearancePath(
    coords: LocationInfo[],
    options: MapRenderOptions,
    color: string,
    dashed: boolean
  ): void {
    if (!coords || coords.length < 2) return;
  
    const ctx = this.ctx;
    const pts: [number, number][] = coords.map(loc => options.project(loc.coord));
    const zoomFactor = options.zoomLevel ?? 1;
    const baseLineWidth = 3.5;
    const scaledLineWidth = baseLineWidth * Math.sqrt(zoomFactor);
  
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(pts[0][0], pts[0][1]);
    for (let i = 1; i < pts.length; i++) {
      ctx.lineTo(pts[i][0], pts[i][1]);
    }
  
    ctx.lineWidth = scaledLineWidth;
    ctx.strokeStyle = color;
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';
    if (dashed) ctx.setLineDash([10, 20]);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.restore();
  
    const minZoomForLabels = 4.0;
    if (zoomFactor >= minZoomForLabels) {
      ctx.save();
      const fontSize = 10 * Math.sqrt(zoomFactor);
      ctx.font = `bold ${fontSize}px sans-serif`;
      ctx.fillStyle = 'white';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
  
      for (let i = 0; i < coords.length; i++) {
        const pt = pts[i];
        const label = coords[i].name;
        if (!label) continue;
  
        ctx.fillText(label, pt[0], pt[1] - 12);
      }
  
      ctx.restore();
    }
  }
  
  
  private drawFinalDestinationMarker(
    ctx: CanvasRenderingContext2D,
    project: (coord: LonLat) => [number, number],
    finalPos: LonLat,
    color: string = AIRPORT_STYLES.pointFill,
    label?: string
  ): void {
    const [fx, fy] = project(finalPos);
  
    ctx.save();
    ctx.beginPath();
    ctx.arc(fx, fy, 6, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();
    ctx.restore();
  
    if (label) {
      ctx.save();
      ctx.font = `12px sans-serif`;
      ctx.fillStyle = color;
      ctx.textAlign = 'left';
      ctx.fillText(label, fx + 8, fy);
      ctx.restore();
    }
  }
  
  // helpers
  private getActivePilotSteps(pilot: PilotPublicView): StepEvent[] {
    const validStatuses = [StepStatus.NEW, StepStatus.LOADED, StepStatus.EXECUTED, StepStatus.STANDBY];
    return Object.values(pilot.steps || {}).filter(step => validStatuses.includes(step.status));
  }

  shortenLabelFromStepCode(stepCode: string): string {
    const label = LABELS[stepCode]?.toLowerCase() ?? stepCode.toLowerCase();
  
    const predefined: Record<string, string> = {
      'expected taxi clearance': 'exp.taxi.clear',
      'taxi clearance': 'taxi.clear',
      'engine startup': 'eng.start',
      'pushback': 'pushb',
      'de_icing': 'deice',
      'voice contact': 'voice',
    };
  
    if (predefined[label]) {
      return predefined[label];
    }
  
    return label
      .replace(/[^a-z0-9\s]/gi, '')
      .split(/\s+/)
      .map(word => word.slice(0, 4))
      .join('.');
  }
  

  setPlaneImage(): void {
    this.planeImage = new Image();
    this.planeImage.onload = () => {
      this.planeImageLoaded = true;
    };
    this.planeImage.src = 'data:image/svg+xml;base64,' + btoa(`
      <svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
        <path
          d="M42 19.3v16.2L9.4 55C6.1 56.7 4 59.7 4 63.1v5.3l38.1-13.2v6c0 1 .1 2.1.2 3.1l3.1 20.9-8.7 6.4v5.9h26.6v-5.9l-8.7-6.4 3.1-20.9c.1-1 .2-2 .2-3.1v-6L96 68.4v-5.3c0-3.4-2.1-6.5-5.4-8.1L57.9 35.5V19.4c0-4.9-3.6-16.9-8-16.9S42 14.3 42 19.3z"
          fill="#e2e8f0"
        />
      </svg>
    `);
  }
  
  // LINES METHODS //
  drawAllLineLabels(
    items: { start: LonLat; end: LonLat; name?: string }[],
    options: MapRenderOptions
  ): void {
    const seenLabels = new Set<string>();
    const zoom = options.zoomLevel ?? 1;
    const usedBoundingBoxes: DOMRect[] = [];
  
    for (const item of items) {
      const name = item.name;
      if (!name || seenLabels.has(name)) continue;
  
      const projectedPoints = [item.start, item.end].map(options.project);
      if (projectedPoints.length < 2 || !this.isVisible(projectedPoints)) continue;
      if (!options.showLabels || zoom < 2) continue;
  
      this.drawLineLabel(name, projectedPoints, zoom, usedBoundingBoxes);
      seenLabels.add(name);
    }
  }
  
  private isVisible(pts: [number, number][]): boolean {
    return pts.some(([x, y]) =>
      x >= 0 && x <= this.ctx.canvas.width &&
      y >= 0 && y <= this.ctx.canvas.height
    );
  }
  
  private drawLinePath(
    points: [number, number][],
    color: string,
    feature: { name?: string; status?: string },
    zoom: number
  ): void {
    const { ctx } = this;
  
    ctx.beginPath();
    ctx.moveTo(...points[0]);
    points.slice(1).forEach(([x, y]) => ctx.lineTo(x, y));
  
    ctx.strokeStyle = color;
    ctx.lineWidth = (AIRPORT_STYLES.strokeWidth ?? 2) * (1 + Math.pow(zoom, 1.1) / 2);
    ctx.setLineDash(this.getLineDash(feature));
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';
    ctx.stroke();
    ctx.setLineDash([]);
  }
  
  
  private drawLineLabel(
    name: string,
    points: [number, number][],
    zoom: number,
    usedBoundingBoxes: DOMRect[]
  ): void {
    const { ctx } = this;
  
    const midIdx = Math.floor(points.length / 2);
    const [x1, y1] = points[midIdx - 1] || points[0];
    const [x2, y2] = points[midIdx] || points[1];
    const midX = (x1 + x2) / 2;
    const midY = (y1 + y2) / 2;
    const angle = Math.atan2(y2 - y1, x2 - x1);
  
    const fontSize = Math.max(8, 9 + (zoom - 1) * 1.2);
    const padding = 5;
    const bgRadius = 4;
  
    ctx.font = `bold ${fontSize}px "Inter", sans-serif`;
    const textWidth = ctx.measureText(name).width;
    const rectWidth = textWidth + 2 * padding;
    const rectHeight = fontSize + 4;
  
    const bbox = new DOMRect(midX - rectWidth / 2, midY - rectHeight / 2, rectWidth, rectHeight);
  
    const isOverlapping = usedBoundingBoxes.some(b =>
      !(bbox.right < b.left || bbox.left > b.right || bbox.bottom < b.top || bbox.top > b.bottom)
    );
  
    if (isOverlapping) return;
    usedBoundingBoxes.push(bbox);
  
    ctx.save();
    ctx.translate(midX, midY);
    ctx.rotate(angle);
  
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
  
    ctx.fillStyle = 'rgba(15, 23, 42, 0.7)';
    this.drawRoundedRect(ctx, -rectWidth / 2, -rectHeight / 2, rectWidth, rectHeight, bgRadius);
    ctx.fill();
  
    ctx.fillStyle = AIRPORT_STYLES.pointLabel;
    ctx.fillText(name, 0, 0);
  
    ctx.restore();
  }
  

  private drawRoundedRect(
    ctx: CanvasRenderingContext2D,
    x: number,
    y: number,
    width: number,
    height: number,
    radius: number
  ): void {
    ctx.beginPath();
    ctx.moveTo(x + radius, y);
    ctx.lineTo(x + width - radius, y);
    ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
    ctx.lineTo(x + width, y + height - radius);
    ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
    ctx.lineTo(x + radius, y + height);
    ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
    ctx.lineTo(x, y + radius);
    ctx.quadraticCurveTo(x, y, x + radius, y);
    ctx.closePath();
  }

     
  // Shared private logic
  private drawLine(
    segments: { start: LonLat; end: LonLat; name?: string }[],
    options: MapRenderOptions,
    defaultColor: string
  ): void {
    const zoom = options.zoomLevel ?? 1;
  
    for (const segment of segments) {
      const projectedPoints = [segment.start, segment.end].map(options.project);
      const strokeColor = defaultColor;
      this.drawLinePath(projectedPoints, strokeColor, segment, zoom);
    }
  }
  
  private drawPoint(
    points: { location: LonLat; name?: string }[],
    options: MapRenderOptions,
    defaultColor: string
  ): void {
    const { ctx } = this;
    const zoom = options.zoomLevel ?? 1;
  
    for (const point of points) {
      const [x, y] = options.project(point.location);
  
      ctx.beginPath();
      ctx.arc(x, y, 3 * Math.min(zoom, 1), 0, 2 * Math.PI);
      ctx.fillStyle = defaultColor;
      ctx.fill();
      ctx.strokeStyle = AIRPORT_STYLES.outline;
      ctx.lineWidth = 1;
      ctx.stroke();
  
      if (options.showLabels && point.name && zoom >= 4.5) {
        ctx.font = 'bold 10px "Inter", sans-serif';
        ctx.fillStyle = AIRPORT_STYLES.pointLabel;
        ctx.strokeStyle = AIRPORT_STYLES.pointLabelStroke;
        ctx.lineWidth = 2;
        ctx.textAlign = 'left';
        ctx.textBaseline = 'bottom';
        ctx.strokeText(point.name, x + 8, y - 6);
        ctx.fillText(point.name, x + 8, y - 6);
      }
    }
  }
  
  
  // private getStrokeColor(feat: GeoJSONFeature): string {
  //   switch (feat.properties?.type) {
  //     case 'runway': return AIRPORT_STYLES.runway;
  //     case 'taxiway': return AIRPORT_STYLES.taxiway;
  //     case 'helipad': return AIRPORT_STYLES.helipad;
  //     case 'parking': return AIRPORT_STYLES.parking;
  //     default: return AIRPORT_STYLES.outline;
  //   }
  // }

  private getLineDash(obj: { status?: string }): number[] {
    return obj.status === 'LOADED' ? [6, 4] : [];
  }
}
