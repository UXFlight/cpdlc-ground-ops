import { FormsModule } from '@angular/forms';
import { Component, HostListener, OnDestroy, OnInit } from '@angular/core';
import { MainPageService } from '@app/services/main-page.service';
import { animate, style, transition, trigger } from '@angular/animations';
import { Subscription } from 'rxjs';
import { AirportMapComponent } from '../airport-map/airport-map.component';
import { AirportMapService } from '@app/services/airport-map.service';
import { Clearance, PilotPublicView, StepPublicView } from '@app/interfaces/Publics';
import { NgStyle } from '@angular/common';
import { RequestLogComponent } from '../selected-pilot/request-log/request-log.component';
import { ClearancesStickerComponent } from '../clearances-sticker/clearances-sticker.component';
import { SelectedRequestInfo } from '@app/interfaces/SelectedRequest';
import { ClearanceBlockComponent } from './clearance-block/clearance-block.component';
import { Atc } from '@app/interfaces/Atc';

enum CardinalDirection {
  N = 'N',
  NE = 'NE',
  E = 'E',
  SE = 'SE',
  S = 'S',
  SO = 'SO',
  O = 'O',
  NO = 'NO',
}

@Component({
  selector: 'app-logs',
  standalone: true,
  imports: [
    FormsModule,
    AirportMapComponent,
    RequestLogComponent,
    NgStyle,
    ClearancesStickerComponent,
    ClearanceBlockComponent,
  ],
  templateUrl: './logs.component.html',
  styleUrl: './logs.component.scss',
  animations: [
    trigger('pilotChange', [
      transition(':enter', [
        style({ opacity: 0, transform: 'translateY(-8px)' }),
        animate(
          '300ms ease-out',
          style({ opacity: 1, transform: 'translateY(0)' })
        ),
      ]),
      transition(':leave', [
        animate(
          '200ms ease-in',
          style({ opacity: 0, transform: 'translateY(8px)' })
        ),
      ]),
    ]),
  ],
})
export class LogsComponent implements OnInit, OnDestroy {
  private selectedAircraftSubscription?: Subscription;
  private pilotsSubscription?: Subscription;
  private atcListSubscription?: Subscription;
  private selectedRequestSubscription?: Subscription;

  readonly maxVisibleAtcIndicators = 4;

  selectedAircraft: PilotPublicView | null = null;
  pilots: PilotPublicView[] = [];
  atcList: Atc[] = [];

  selectedRequestInfo: SelectedRequestInfo = {
    stepCode: '',
    requestId: '',
  };

  controlsPanelActive = true;
  currIdx = 0;

  constructor(
    private readonly mainPageService: MainPageService,
    private readonly airportMapService: AirportMapService
  ) {}

  ngOnInit(): void {
    this.configSubscription();
  }

  ngOnDestroy(): void {
    this.selectedAircraftSubscription?.unsubscribe();
    this.pilotsSubscription?.unsubscribe();
    this.selectedRequestSubscription?.unsubscribe();
    this.atcListSubscription?.unsubscribe();
  }

  get focusedAtcs(): Atc[] {
    if (!this.selectedAircraft) return [];

    return this.atcList.filter(
      (atc) => atc.selectedAircraft === this.selectedAircraft?.sid
    );
  }

  get focusedAtcsTitle(): string {
    return `Aircraft currently viewed by controllers: ${this.focusedAtcs
      .map((atc) => atc.sid)
      .join(', ')}`;
  }

  configSubscription(): void {
    this.pilotsSubscription = this.mainPageService.pilotsPreviews$.subscribe((pilots) => {
      this.pilots = pilots;
    });

    this.selectedAircraftSubscription = this.airportMapService.selectedAircraft$.subscribe((aircraft) => {
      if (!aircraft) this.airportMapService.resetZoomAndPan();

      this.selectedAircraft = aircraft;
      this.currIdx = 0;
    });

    this.selectedRequestSubscription = this.mainPageService.selectedRequestId$.subscribe(
      (requestInfo: SelectedRequestInfo) => {
        this.selectedRequestInfo = requestInfo;
      }
    );

    this.atcListSubscription = this.mainPageService.atcList$.subscribe((atcList: Atc[]) => {
      this.atcList = atcList;
    });
  }

  getActiveSteps(pilot: PilotPublicView): StepPublicView[] {
    return this.mainPageService
      .getActiveStep(pilot.sid)
      .filter((step) => !['DM_135', 'DM_136'].includes(step.step_code));
  }

  navigateToPilot(direction: 'next' | 'prev'): void {
    const pilots = this.mainPageService.pilotsPreviewsSubject.getValue();
    if (!this.selectedAircraft || pilots.length === 0) return;

    this.airportMapService.navigateToPilot(pilots, direction);
  }

  hasMultiplePilot(): boolean {
    const pilots = this.mainPageService.pilotsPreviewsSubject.getValue();
    return pilots.length > 1;
  }

  @HostListener('window:keydown', ['$event'])
  handleKeyDown(event: KeyboardEvent): void {
    if (event.key === 'Tab') {
      event.preventDefault();
      this.controlsPanelActive = !this.controlsPanelActive;
      return;
    }

    if (event.key === 'Escape') return this.airportMapService.resetZoom();

    if (event.ctrlKey && event.key === 'r') {
      event.preventDefault();
      return this.airportMapService.resetZoom();
    }

    if (event.ctrlKey && event.key === 's') {
      event.preventDefault();
      return this.airportMapService.toggleLabels();
    }

    if (event.key === 'ArrowLeft') {
      return this.airportMapService.navigateToPilot(this.pilots, 'prev');
    }

    if (event.key === 'ArrowRight') {
      return this.airportMapService.navigateToPilot(this.pilots, 'next');
    }

    if (!this.selectedAircraft) return;

    const planeSteps = Object.values(this.selectedAircraft.steps).filter(
      (step) => !['DM_135', 'DM_136'].includes(step.step_code)
    );

    const len = planeSteps.length;

    if (len === 0) return;

    const requestInfo: SelectedRequestInfo = {
      stepCode: planeSteps[this.currIdx].step_code,
      requestId: planeSteps[this.currIdx].request_id,
    };

    if (event.key === 'ArrowUp') {
      this.currIdx = (this.currIdx - 1 + len) % len;
      return this.mainPageService.selectRequest(requestInfo);
    }

    if (event.key === 'ArrowDown') {
      this.currIdx = (this.currIdx + 1) % len;
      return this.mainPageService.selectRequest(requestInfo);
    }
  }

  formatHeading(heading: number): string {
    return `${this.parseHeadingToCardinal(heading)} (${heading.toFixed(2)}°)`;
  }

  parseHeadingToCardinal(heading: number): CardinalDirection {
    const normalized = ((heading % 360) + 360) % 360;

    if (normalized >= 337.5 || normalized < 22.5) return CardinalDirection.N;
    if (normalized < 67.5) return CardinalDirection.NE;
    if (normalized < 112.5) return CardinalDirection.E;
    if (normalized < 157.5) return CardinalDirection.SE;
    if (normalized < 202.5) return CardinalDirection.S;
    if (normalized < 247.5) return CardinalDirection.SO;
    if (normalized < 292.5) return CardinalDirection.O;

    return CardinalDirection.NO;
  }

  getMRecentClearance(): Clearance | null {
    if (!this.selectedAircraft || !this.selectedAircraft.clearances) return null;

    const priority = ['route_change', 'taxi', 'expected'];

    for (const kind of priority) {
      const clearance = this.selectedAircraft.clearances[kind];
      if (clearance && clearance.instruction.trim() !== '') return clearance;
    }

    return null;
  }
}