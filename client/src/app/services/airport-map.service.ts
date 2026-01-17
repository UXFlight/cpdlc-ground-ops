import { Injectable } from '@angular/core';
// import { CommunicationService } from './communication.service';
import { BehaviorSubject, Observable } from 'rxjs';
import { MapRenderOptions } from '@app/classes/airport-map-renderer.ts';
import { Clearance, ClearancePayload, PilotPublicView } from '@app/interfaces/Publics';
import { ClientSocketService } from './client-socket.service';
import { AirportMapData } from '@app/interfaces/AirMap';

@Injectable({ providedIn: 'root' })
export class AirportMapService {
  airportMapSubject = new BehaviorSubject<AirportMapData | null>(null);
  airportMap$: Observable<AirportMapData | null> = this.airportMapSubject.asObservable();

  private loadedRouteSubject = new BehaviorSubject<AirportMapData[]>([]);
  loadedRoute$: Observable<AirportMapData[]> = this.loadedRouteSubject.asObservable();

  private executedRouteSubject = new BehaviorSubject<AirportMapData[]>([]);
  executedRoute$: Observable<AirportMapData[]> = this.executedRouteSubject.asObservable();

  selectedPlaneSubject = new BehaviorSubject<PilotPublicView | null>(null);
  selectedPlane$: Observable<PilotPublicView | null> = this.selectedPlaneSubject.asObservable();

  renderSubject = new BehaviorSubject<boolean>(false);
  render$: Observable<boolean> = this.renderSubject.asObservable();

  private showLabelsSubject = new BehaviorSubject<boolean>(false);
  showLabels$: Observable<boolean> = this.showLabelsSubject.asObservable();

  // === Projection data ===
  private baseScale = 1;
  private minLon = 0;
  private maxLon = 0;
  private minLat = 0;
  private maxLat = 0;
  private padding = 50;

  private offsetCenterX = 0;
  private offsetCenterY = 0;

  private canvasWidth = 0;
  private canvasHeight = 0;

  // zoom/pan/rotation
  zoomFactor = 1;
  private panOffset = { x: 0, y: 0 };
  private rotationAngle = 0; // radians

  private readonly MIN_ZOOM = 0.2;
  private readonly MAX_ZOOM = 20;
  private readonly PAN_SENSITIVITY = 1;
  private readonly ZOOM_SENSITIVITY = 0.0016;
  private readonly ZOOM_SMOOTHING = 0.2;

  private zoomTarget = 1;
  private panTarget = { x: 0, y: 0 };
  private zoomAnimationId = 0;
  private prefersReducedMotion = false;

  constructor(
    // private readonly communicationService: CommunicationService,
    private readonly socketClientService: ClientSocketService
  ) {
    this.prefersReducedMotion =
      typeof window !== 'undefined' &&
      window.matchMedia &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    this.listenToSocketEvents();
  }

  private listenToSocketEvents(): void {
    this.socketClientService.listen('airport_map_data', this.onAirportMapData);

    this.socketClientService.listen<ClearancePayload>('proposed_clearance', this.updatePilotClearance);
    
  }

  fetchAirportMapData(): void {
    this.socketClientService.send('getAirportMapData');
  }

  updateCanvasSize(width: number, height: number): void {
    this.canvasWidth = width;
    this.canvasHeight = height;
    this.computeProjection();
  }

  private computeProjection(): void {
    const map = this.airportMapSubject.value;
    if (!map) return;
  
    // === Collect all LonLat coordinates ===
    const allCoords: [number, number][] = [];
  
    map.runways.forEach(rw => {
      allCoords.push(rw.start, rw.end);
    });
  
    map.helipads.forEach(h => {
      allCoords.push(h.location);
    });
  
    map.taxiways.forEach(t => {
      allCoords.push(t.start, t.end);
    });
  
    map.parking.forEach(p => {
      allCoords.push(p.location);
    });
  
    if (!allCoords.length) return;
  
    // === Extract bounds ===
    const lons = allCoords.map(([lon, _]) => lon);
    const lats = allCoords.map(([_, lat]) => lat);
    this.minLon = Math.min(...lons);
    this.maxLon = Math.max(...lons);
    this.minLat = Math.min(...lats);
    this.maxLat = Math.max(...lats);
  
    // === Compute scaling factors ===
    const W = this.canvasWidth - 2 * this.padding;
    const H = this.canvasHeight - 2 * this.padding;
    const scaleX = W / (this.maxLon - this.minLon);
    const scaleY = H / (this.maxLat - this.minLat);
    this.baseScale = Math.min(scaleX, scaleY);
  
    // === Center offset ===
    const projectedWidth = (this.maxLon - this.minLon) * this.baseScale;
    const projectedHeight = (this.maxLat - this.minLat) * this.baseScale;
    this.offsetCenterX = (this.canvasWidth - projectedWidth) / 2;
    this.offsetCenterY = (this.canvasHeight - projectedHeight) / 2;
  }
  
  getRenderOptions(): MapRenderOptions | null {
    if (!this.canvasWidth || !this.canvasHeight || !this.airportMapSubject.value) return null;

    const rawProject = ([lon, lat]: [number, number]): [number, number] => [
      this.offsetCenterX + (lon - this.minLon) * this.baseScale,
      this.canvasHeight - (this.offsetCenterY + (lat - this.minLat) * this.baseScale)
    ];

    const project = (coord: [number, number]): [number, number] => {
      const [x0, y0] = rawProject(coord);
      const scaledX = x0 * this.zoomFactor;
      const scaledY = y0 * this.zoomFactor;
      const [rotX, rotY] = this.rotatePoint(
        scaledX,
        scaledY,
        this.rotationAngle,
        this.canvasWidth / 2,
        this.canvasHeight / 2
      );

      return [rotX + this.panOffset.x, rotY + this.panOffset.y];
    };

    return {
      project,
      showLabels: this.showLabelsSubject.value,
      zoomLevel: this.zoomFactor,
      rotation: this.rotationAngle
    };
  }

  // external controls for zoom/pan
  setZoomAndPan(zoom: number, pan: { x: number; y: number }): void {
    this.zoomFactor = this.clampZoom(zoom);
    this.panOffset = { ...pan };
    this.renderSubject.next(true);
  }

  private rawProject([lon, lat]: [number, number]): [number, number] {
    return [
      this.offsetCenterX + (lon - this.minLon) * this.baseScale,
      this.canvasHeight - (this.offsetCenterY + (lat - this.minLat) * this.baseScale)
    ];
  }
  
  centerOnCoordinate(coord: [number, number], zoom: number): { x: number; y: number } {
    const [x0, y0] = this.rawProject(coord);
    const canvasCenterX = this.canvasWidth / 3; // slighty to the left, this.canvasWidth/2 to center 
    const canvasCenterY = this.canvasHeight / 2;

    const [rotX, rotY] = this.rotatePoint(
      x0 * zoom,
      y0 * zoom,
      this.rotationAngle,
      this.canvasWidth / 2,
      this.canvasHeight / 2
    );

    return {
      x: canvasCenterX - rotX,
      y: canvasCenterY - rotY
    };
  }

  navigateToPilot(pilots: PilotPublicView[], direction: string): void {
    const sid = this.selectedPlaneSubject.value?.sid;
    if (pilots.length === 0) return;

    let index = 0;

    if (sid) index = pilots.findIndex(p => p.sid === sid)
    if (index === -1) return;
  
    const newIndex =
      direction === 'next'
        ? (index + 1) % pilots.length
        : (index - 1 + pilots.length) % pilots.length;
        
    this.focusOnPilot(pilots[newIndex]);
  }

  focusOnPilot(pilot: PilotPublicView, zoomLevel = 2): void {
    this.socketClientService.send('selectPilot', pilot.sid);
    const selectedPlane = this.selectedPlaneSubject.value;
    if (selectedPlane && selectedPlane.sid === pilot.sid) return this.resetZoom();
    this.selectPlane(pilot);
  
    const pan = this.centerOnCoordinate(pilot.plane!.current_pos.coord, zoomLevel);
    this.animateZoomAndPan(zoomLevel, pan);
  }
  
  
  animateZoomAndPan(targetZoom: number, targetPan: { x: number; y: number }, duration = 300): void {
    if (this.prefersReducedMotion) {
      this.setZoomAndPan(targetZoom, targetPan);
      return;
    }

    const startZoom = this.zoomFactor;
    const startPan = { ...this.panOffset };

    const startTime = performance.now();
  
    const animate = (now: number) => {
      const t = Math.min(1, (now - startTime) / duration);
  
      const easedT = t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
  
      const zoom = startZoom + (targetZoom - startZoom) * easedT;
      const panX = startPan.x + (targetPan.x - startPan.x) * easedT;
      const panY = startPan.y + (targetPan.y - startPan.y) * easedT;
  
      this.setZoomAndPan(zoom, { x: panX, y: panY });
  
      if (t < 1) {
        requestAnimationFrame(animate);
      }
    };
  
    requestAnimationFrame(animate);
  }
  
  resetZoom(): void {
    this.resetZoomAndPan();
    this.resetPlaneSelection()
  }

  resetZoomAndPan(): void {
    this.zoomFactor = 1;
    this.panOffset = { x: 0, y: 0 };
    this.rotationAngle = 0;
    this.animateZoomAndPan(this.zoomFactor, this.panOffset, 300);
    this.renderSubject.next(true);
  }

  resetPlaneSelection(): void {
    const currentPlaneSid = this.selectedPlaneSubject.value?.sid;
    if (!currentPlaneSid) return;
    this.socketClientService.send('selectPilot', currentPlaneSid);
    this.selectedPlaneSubject.next(null);
  }

  zoomResetted(): boolean {
    return this.zoomFactor !== 1 ||
      this.panOffset.x !== 0 ||
      this.panOffset.y !== 0 ||
      this.rotationAngle !== 0;
  }

  zoomFromWheel(deltaY: number, center: [number, number]): void {
    const zoomChange = Math.exp(-deltaY * this.ZOOM_SENSITIVITY);
    const newZoom = this.clampZoom(this.zoomFactor * zoomChange);
    const newPan = this.computePanForZoom(newZoom, center);

    this.zoomTarget = newZoom;
    this.panTarget = newPan;

    if (this.prefersReducedMotion) {
      this.setZoomAndPan(this.zoomTarget, this.panTarget);
      return;
    }

    if (!this.zoomAnimationId) {
      this.zoomAnimationId = requestAnimationFrame(this.animateZoomStep);
    }
  }

  selectPlane(plane: PilotPublicView | null): void {
    this.selectedPlaneSubject.next(plane);
  }

  toggleLabels(): void {
    this.showLabelsSubject.next(!this.showLabelsSubject.value);
  }
  // event
  applyPan(dx: number, dy: number): void {
    this.panOffset.x += dx * this.PAN_SENSITIVITY;
    this.panOffset.y += dy * this.PAN_SENSITIVITY;
  }

  getBaseScale(): number {
    return this.baseScale || 1; // fallback pour éviter division par 0
  }

  rotateBy(deltaRadians: number): void {
    this.setRotation(this.rotationAngle + deltaRadians);
  }

  setRotation(angleRadians: number): void {
    const normalized = Math.atan2(Math.sin(angleRadians), Math.cos(angleRadians));
    this.rotationAngle = normalized;
    this.renderSubject.next(true);
  }

  zoomByFactor(factor: number, center: [number, number]): void {
    const newZoom = this.clampZoom(this.zoomFactor * factor);
    const newPan = this.computePanForZoom(newZoom, center);
    this.zoomTarget = newZoom;
    this.panTarget = newPan;

    if (this.prefersReducedMotion) {
      this.setZoomAndPan(this.zoomTarget, this.panTarget);
      return;
    }

    if (!this.zoomAnimationId) {
      this.zoomAnimationId = requestAnimationFrame(this.animateZoomStep);
    }
  }

  private computePanForZoom(newZoom: number, center: [number, number]): { x: number; y: number } {
    const [cx, cy] = center;
    const currentZoom = this.zoomFactor || 1;
    const unpannedX = cx - this.panOffset.x;
    const unpannedY = cy - this.panOffset.y;
    const [unrotX, unrotY] = this.rotatePoint(
      unpannedX,
      unpannedY,
      -this.rotationAngle,
      this.canvasWidth / 2,
      this.canvasHeight / 2
    );
    const baseX = unrotX / currentZoom;
    const baseY = unrotY / currentZoom;
    const [rotX, rotY] = this.rotatePoint(
      baseX * newZoom,
      baseY * newZoom,
      this.rotationAngle,
      this.canvasWidth / 2,
      this.canvasHeight / 2
    );

    return {
      x: cx - rotX,
      y: cy - rotY
    };
  }

  private clampZoom(zoom: number): number {
    return Math.min(this.MAX_ZOOM, Math.max(this.MIN_ZOOM, zoom));
  }

  private rotatePoint(
    x: number,
    y: number,
    angle: number,
    cx: number,
    cy: number
  ): [number, number] {
    const dx = x - cx;
    const dy = y - cy;
    const cos = Math.cos(angle);
    const sin = Math.sin(angle);
    return [cx + dx * cos - dy * sin, cy + dx * sin + dy * cos];
  }

  private animateZoomStep = () => {
    const zoomDelta = this.zoomTarget - this.zoomFactor;
    const panDeltaX = this.panTarget.x - this.panOffset.x;
    const panDeltaY = this.panTarget.y - this.panOffset.y;
    const closeEnough =
      Math.abs(zoomDelta) < 0.001 &&
      Math.abs(panDeltaX) < 0.25 &&
      Math.abs(panDeltaY) < 0.25;

    if (closeEnough) {
      this.setZoomAndPan(this.zoomTarget, this.panTarget);
      this.zoomAnimationId = 0;
      return;
    }

    this.zoomFactor += zoomDelta * this.ZOOM_SMOOTHING;
    this.panOffset.x += panDeltaX * this.ZOOM_SMOOTHING;
    this.panOffset.y += panDeltaY * this.ZOOM_SMOOTHING;
    this.renderSubject.next(true);

    this.zoomAnimationId = requestAnimationFrame(this.animateZoomStep);
  }

  // === Socket events ===
  private onAirportMapData = (data: AirportMapData): void => {
    this.airportMapSubject.next(data);
    this.computeProjection();
  }

  private updatePilotClearance = (payload: ClearancePayload): void => {
    const currentPlane = this.selectedPlaneSubject.value;
    if (!currentPlane || currentPlane.sid !== payload.pilot_sid) return;

    const { kind, instruction, coords, issued_at } = payload.clearance;

    const clearance: Clearance = {
      kind: kind,
      instruction: instruction,
      coords: coords,
      issued_at: issued_at,
    };

    currentPlane.clearances[kind] = clearance;
    this.selectedPlaneSubject.next(currentPlane);
  }
}
