import { FormsModule } from '@angular/forms';
import { Component, HostListener, OnDestroy, OnInit } from '@angular/core';
import { MainPageService } from '@app/services/main-page.service';
import { animate, style, transition, trigger } from '@angular/animations';
import { LABELS } from '@app/modules/constants';
import { Subscription } from 'rxjs';
import { SelectedPilotComponent } from '../selected-pilot/selected-pilot.component';
import { AirportMapComponent } from '../airport-map/airport-map.component';
import { AirportMapService } from '@app/services/airport-map.service';
import { Clearance, PilotPublicView, StepPublicView } from '@app/interfaces/Publics';
import { NgStyle } from '@angular/common';
import { RequestLogComponent } from '../selected-pilot/request-log/request-log.component';
import { ClearancesStickerComponent } from '../clearances-sticker/clearances-sticker.component';
import { SelectedRequestInfo } from '@app/interfaces/SelectedRequest';
import { ClearanceBlockComponent } from './clearance-block/clearance-block.component';

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
  imports: [FormsModule, AirportMapComponent, SelectedPilotComponent, RequestLogComponent, NgStyle, ClearancesStickerComponent, ClearanceBlockComponent],
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
  private selectedPilotSubscription: Subscription;
  private selectedPlaneSubscription: Subscription;

  selectedPilotSid: string | null = null;
  selectedPlane: PilotPublicView | null = null;

  defaultLabels = LABELS;

  // events attributes
  controlsPanelActive = true;

  currIdx = 0;
  pilots: PilotPublicView[] = [];

  selectedRequestInfo: SelectedRequestInfo = {
    stepCode: '',
    requestId: ''
  };

  // sunscriptions
  selectedRequestSubscription: Subscription;
  pilotsSubscription: Subscription;

  constructor(
    private readonly mainPageService: MainPageService,
    private readonly airportMapService: AirportMapService
  ) {
  }

  ngOnInit(): void {
    this.configSubscription();
  }

  ngOnDestroy(): void {
    this.selectedPilotSubscription?.unsubscribe();
    this.selectedPlaneSubscription?.unsubscribe();
  }

  configSubscription(): void {
    this.selectedPilotSubscription = this.mainPageService.selectedPilot$.subscribe((pilot) => {
      this.selectedPilotSid = pilot ? pilot.sid : null;
      this.controlsPanelActive = !!!this.selectedPilotSid
    });

    this.selectedPlaneSubscription = this.airportMapService.selectedPlane$.subscribe((plane) => {
        if (!plane) this.airportMapService.resetZoomAndPan();
        this.selectedPlane = plane;
        this.currIdx = 0;
    });

    this.selectedRequestSubscription = this.mainPageService.selectedRequestId$.subscribe((requestInfo: SelectedRequestInfo) => {
      this.selectedRequestInfo = requestInfo;
    });

    this.pilotsSubscription = this.mainPageService.pilotsPreviews$.subscribe((pilots) => {
        this.pilots = pilots;
    });
  }

  viewPilotLogs(): void {
    if (this.selectedPlane) {
      this.mainPageService.selectPilot(this.selectedPlane.sid, false);
      this.selectedPlane = null; 
    }
  }

  getActiveSteps(pilot: PilotPublicView): StepPublicView[] {
    return this.mainPageService.getActiveStep(pilot.sid).filter(step => !['DM_135', 'DM_136'].includes(step.step_code));
  }

  navigateToPilot(direction: 'next' | 'prev'): void {
    const pilots = this.mainPageService.pilotsPreviewsSubject.getValue();
    if (!this.selectedPlane || pilots.length === 0) return;

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
      return
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

    if (event.key === 'ArrowLeft') return this.airportMapService.navigateToPilot(this.pilots, 'prev');
    if (event.key === 'ArrowRight') return this.airportMapService.navigateToPilot(this.pilots, 'next');

    if (!this.selectedPlane) return;
    const planeSteps = Object.values(this.selectedPlane.steps);
    const len = planeSteps.length;
    let requestInfo: SelectedRequestInfo = {
        stepCode: '',
        requestId: ''
    };

    if (event.key === 'ArrowUp') {
        if (len === 0) return;
        requestInfo.stepCode = planeSteps[this.currIdx].step_code;
        requestInfo.requestId = planeSteps[this.currIdx].request_id;
        this.currIdx = (this.currIdx - 1 + len) % len;;

        return this.mainPageService.selectRequest(requestInfo);
    }

    if (event.key === 'ArrowDown') {
        if (len === 0) return;
        requestInfo.stepCode = planeSteps[this.currIdx].step_code;
        requestInfo.requestId = planeSteps[this.currIdx].request_id;
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

  // clearances
  getMRecentClearance(): Clearance | null {
    if (!this.selectedPlane || !this.selectedPlane.clearances) return null;
  
    const priority = ["route_change", "taxi", "expected"];
  
    for (const kind of priority) {
      const c = this.selectedPlane.clearances[kind];
      if (c && c.instruction.trim() !== "") return c;
    }
  
    return null;
  }
}