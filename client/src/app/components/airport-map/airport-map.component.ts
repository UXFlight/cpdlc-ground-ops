import {
  AfterViewInit,
  Component,
  ElementRef,
  OnDestroy,
  OnInit,
  ViewChild,
  HostListener
} from '@angular/core';
import { Subscription } from 'rxjs';
import { AirportMapService } from '@app/services/airport-map.service';
import { AirportMapData } from '@app/interfaces/AirMap';
import { PilotPublicView } from '@app/interfaces/Publics';
import { AirportMapRenderer, MapRenderOptions } from '@app/classes/airport-map-renderer.ts';
import { MainPageService } from '@app/services/main-page.service';

@Component({
  selector: 'app-airport-map',
  standalone: true,
  templateUrl: './airport-map.component.html',
  styleUrl: './airport-map.component.scss'
})
export class AirportMapComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild('canvas', { static: true }) canvasRef!: ElementRef<HTMLCanvasElement>;

  showLabels = false;
  showLabelsSubscription!: Subscription;

  private ctx!: CanvasRenderingContext2D;
  private renderer!: AirportMapRenderer;
  private pilotSubscription!: Subscription;
  private airportMapSubscription!: Subscription;
  private renderSubject!: Subscription;

  pilots: PilotPublicView[] = [];
  airportMap: AirportMapData | null = null;

  private isDragging = false;
  private activePointerId: number | null = null;
  private lastPointerX = 0;
  private lastPointerY = 0;
  private dragMoved = false;
  private pendingPan = { x: 0, y: 0 };
  private panAnimationId = 0;
  private renderAnimationId = 0;

  private readonly DRAG_THRESHOLD_PX = 4;
  private readonly KEY_PAN_STEP = 40;
  private readonly KEY_ZOOM_STEP = 1.12;
  private readonly ROTATION_STEP = Math.PI / 18;

  constructor(
    private readonly mainpageService: MainPageService,
    private readonly airportMapService: AirportMapService
  ) {}

  ngOnInit(): void {
    this.configSubscriptions();
    this.airportMapService.fetchAirportMapData();
  }

  ngAfterViewInit(): void {
    const canvas = this.canvasRef.nativeElement;
    this.ctx = canvas.getContext('2d')!;
    this.renderer = new AirportMapRenderer(this.ctx, canvas);
    this.canvasRef.nativeElement.addEventListener('wheel', this.onCanvasWheel, { passive: false });
    this.canvasRef.nativeElement.addEventListener('pointerdown', this.onCanvasPointerDown);
    this.canvasRef.nativeElement.addEventListener('pointermove', this.onCanvasPointerMove);
    this.canvasRef.nativeElement.addEventListener('pointerup', this.onCanvasPointerUp);
    this.canvasRef.nativeElement.addEventListener('pointercancel', this.onCanvasPointerUp);
    this.canvasRef.nativeElement.addEventListener('keydown', this.onCanvasKeyDown);
    canvas.tabIndex = 0;
    canvas.setAttribute('role', 'application');
    canvas.setAttribute('aria-label', 'Airport map. Use mouse, touch, or keyboard to pan, zoom, and rotate.');
    canvas.style.touchAction = 'none';
    this.resizeCanvas();
    canvas.addEventListener('click', this.onCanvasClick);
  }
  
  ngOnDestroy(): void {
    this.pilotSubscription?.unsubscribe();
    this.airportMapSubscription?.unsubscribe();
    this.renderSubject?.unsubscribe();
    this.showLabelsSubscription?.unsubscribe();
    const canvas = this.canvasRef?.nativeElement;
    if (canvas) {
      canvas.removeEventListener('wheel', this.onCanvasWheel);
      canvas.removeEventListener('pointerdown', this.onCanvasPointerDown);
      canvas.removeEventListener('pointermove', this.onCanvasPointerMove);
      canvas.removeEventListener('pointerup', this.onCanvasPointerUp);
      canvas.removeEventListener('pointercancel', this.onCanvasPointerUp);
      canvas.removeEventListener('keydown', this.onCanvasKeyDown);
      canvas.removeEventListener('click', this.onCanvasClick);
    }
    if (this.panAnimationId) cancelAnimationFrame(this.panAnimationId);
    if (this.renderAnimationId) cancelAnimationFrame(this.renderAnimationId);
    // this.renderer?.stopPingLoop();
  }

  toggleLabels() {
    this.airportMapService.toggleLabels();
  }

  @HostListener('window:resize')
  onWindowResize() {
    this.resizeCanvas();
    this.scheduleRender();
  }

  // never settle for less UX, this event is only used for the cursor style. 
  @HostListener('mousemove', ['$event'])
  onMouseMove(event: MouseEvent): void {
    const canvas = this.canvasRef.nativeElement;
    if (this.isDragging) return;
  
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
  
    const options = this.airportMapService.getRenderOptions();
  
    const hovered = this.pilots.some(pilot => {
      if (!pilot.plane || !options) return false;
      const [px, py] = options.project(pilot.plane.current_pos.coord);
      const dx = x - px;
      const dy = y - py;
      return Math.sqrt(dx * dx + dy * dy) < 12;
    });
  
    canvas.style.cursor = hovered ? 'pointer' : 'default';
  }

  private resizeCanvas(): void {
    const canvas = this.canvasRef.nativeElement;
    canvas.width = canvas.clientWidth;
    canvas.height = canvas.clientHeight;
    this.airportMapService.updateCanvasSize(canvas.width, canvas.height);
    this.scheduleRender();
  }

  private configSubscriptions(): void {
    this.pilotSubscription = this.mainpageService.pilotsPreviews$.subscribe(pilots => {
      this.pilots = pilots;
      this.scheduleRender();
    });
  
    this.airportMapSubscription = this.airportMapService.airportMap$.subscribe(map => {
      if (!map ) return;
      this.airportMap = map;
  
      const canvas = this.canvasRef.nativeElement;
      this.airportMapService.updateCanvasSize(canvas.width, canvas.height);
  
      this.scheduleRender();
    });

    this.renderSubject = this.airportMapService.render$.subscribe(render => {
      if (render) this.scheduleRender();
    });

    this.showLabelsSubscription = this.airportMapService.showLabels$.subscribe(show => {
      this.showLabels = show;
      this.scheduleRender();
    });
  }

  private render(): void {
    const options: MapRenderOptions | null = this.airportMapService.getRenderOptions();
    if (!this.airportMap || !options || !this.renderer) return;
  
    this.renderer.clear();
  
    this.renderer.drawTaxiways(this.airportMap.taxiways, options);
    this.renderer.drawRunways(this.airportMap.runways, options);
    this.renderer.drawParkings(this.airportMap.parking, options);
    this.renderer.drawHelipads(this.airportMap.helipads, options);
  
    if (this.showLabels) {
      this.renderer.drawAllLineLabels(this.airportMap.taxiways, options);
      }
  
    this.renderer.drawPilots(this.pilots, options);
  }
  
  private scheduleRender(): void {
    if (this.renderAnimationId) return;
    this.renderAnimationId = requestAnimationFrame(() => {
      this.renderAnimationId = 0;
      this.render();
    });
  }

  onResetMap(): void {
    this.airportMapService.resetZoom();
  }

  checkNoZoom() : boolean {
    return this.airportMapService.zoomResetted()
  }

  // On event listeners methods
  private onCanvasWheel = (evt: WheelEvent) => {
    evt.preventDefault();
  
    const canvas = this.canvasRef.nativeElement;
    const rect = canvas.getBoundingClientRect();
    const mouseX = evt.clientX - rect.left;
    const mouseY = evt.clientY - rect.top;
    const delta =
      evt.deltaMode === WheelEvent.DOM_DELTA_LINE
        ? evt.deltaY * 16
        : evt.deltaMode === WheelEvent.DOM_DELTA_PAGE
          ? evt.deltaY * canvas.clientHeight
          : evt.deltaY;
  
    this.airportMapService.zoomFromWheel(delta, [mouseX, mouseY]);
  };

  private onCanvasClick = (event: MouseEvent): void => {
    if (this.dragMoved) return; // if we moved!
    const canvas = this.canvasRef.nativeElement;
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
  
    const options = this.airportMapService.getRenderOptions();
    if (!options) return;
  
    for (const pilot of this.pilots) {
      if (!pilot.plane) continue;
  
      const [projX, projY] = options.project(pilot.plane.current_pos.coord);
      const dx = x - projX;
      const dy = y - projY;
      const dist = Math.sqrt(dx * dx + dy * dy);
  
      if (dist < 12) {
        const ZOOM = 2;
        return this.airportMapService.focusOnPilot(pilot, ZOOM);
      }
    }
    return;
  };

  private onCanvasPointerDown = (event: PointerEvent): void => {
    if (event.pointerType === 'mouse' && event.button !== 0) return;
    this.isDragging = true;
    this.dragMoved = false;
    this.activePointerId = event.pointerId;
    this.lastPointerX = event.clientX;
    this.lastPointerY = event.clientY;
    this.canvasRef.nativeElement.setPointerCapture(event.pointerId);
    this.canvasRef.nativeElement.style.cursor = 'grabbing';
    this.canvasRef.nativeElement.focus({ preventScroll: true });
    if (event.pointerType !== 'mouse') event.preventDefault();
  };

  private onCanvasPointerMove = (event: PointerEvent): void => {
    if (!this.isDragging || event.pointerId !== this.activePointerId) return;
    const dx = event.clientX - this.lastPointerX;
    const dy = event.clientY - this.lastPointerY;
    if (Math.abs(dx) >= this.DRAG_THRESHOLD_PX || Math.abs(dy) >= this.DRAG_THRESHOLD_PX) {
      this.dragMoved = true;
    }
    this.lastPointerX = event.clientX;
    this.lastPointerY = event.clientY;
    this.queuePan(dx, dy);
    if (event.pointerType !== 'mouse') event.preventDefault();
  };

  private onCanvasPointerUp = (event: PointerEvent): void => {
    if (event.pointerId !== this.activePointerId) return;
    this.isDragging = false;
    this.activePointerId = null;
    this.canvasRef.nativeElement.style.cursor = 'default';
    if (this.canvasRef.nativeElement.hasPointerCapture(event.pointerId)) {
      this.canvasRef.nativeElement.releasePointerCapture(event.pointerId);
    }
  };

  private queuePan(dx: number, dy: number): void {
    this.pendingPan.x += dx;
    this.pendingPan.y += dy;
    if (this.panAnimationId) return;

    this.panAnimationId = requestAnimationFrame(() => {
      const { x, y } = this.pendingPan;
      this.pendingPan = { x: 0, y: 0 };
      this.panAnimationId = 0;
      if (x !== 0 || y !== 0) {
        this.airportMapService.applyPan(x, y);
        this.scheduleRender();
      }
    });
  }

  private onCanvasKeyDown = (event: KeyboardEvent): void => {
    if (this.isEditableElement(event.target)) return;
    const key = event.key.toLowerCase();
    const canvas = this.canvasRef.nativeElement;
    const center: [number, number] = [canvas.clientWidth / 2, canvas.clientHeight / 2];

    switch (key) {
      case 'arrowup':
        this.airportMapService.applyPan(0, -this.KEY_PAN_STEP);
        this.scheduleRender();
        event.preventDefault();
        break;
      case 'arrowdown':
        this.airportMapService.applyPan(0, this.KEY_PAN_STEP);
        this.scheduleRender();
        event.preventDefault();
        break;
      case 'arrowleft':
        this.airportMapService.applyPan(-this.KEY_PAN_STEP, 0);
        this.scheduleRender();
        event.preventDefault();
        break;
      case 'arrowright':
        this.airportMapService.applyPan(this.KEY_PAN_STEP, 0);
        this.scheduleRender();
        event.preventDefault();
        break;
      case '+':
      case '=':
        this.airportMapService.zoomByFactor(this.KEY_ZOOM_STEP, center);
        event.preventDefault();
        break;
      case '-':
      case '_':
        this.airportMapService.zoomByFactor(1 / this.KEY_ZOOM_STEP, center);
        event.preventDefault();
        break;
      case 'q':
        this.airportMapService.rotateBy(-this.ROTATION_STEP);
        event.preventDefault();
        break;
      case 'e':
        this.airportMapService.rotateBy(this.ROTATION_STEP);
        event.preventDefault();
        break;
    }
  };

  private isEditableElement(target: EventTarget | null): boolean {
    const element = target as HTMLElement | null;
    if (!element) return false;
    const tag = element.tagName?.toLowerCase();
    return tag === 'input' || tag === 'textarea' || element.isContentEditable;
  }
  
}
