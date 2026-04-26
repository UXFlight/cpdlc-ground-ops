import { NgClass } from '@angular/common';
import { Component, Input, OnDestroy, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Clearance, PilotPublicView } from '@app/interfaces/Publics';
import { StepStatus } from '@app/interfaces/StepStatus';
import { AirportMapService } from '@app/services/airport-map.service';
import { MainPageService } from '@app/services/main-page.service';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-clearance-block',
  standalone: true,
  imports: [FormsModule, NgClass],
  templateUrl: './clearance-block.component.html',
  styleUrl: './clearance-block.component.scss'
})
export class ClearanceBlockComponent implements OnInit, OnDestroy {
  @Input() clearance: Clearance | null;

  showDetails = false;

  selectedPilot: PilotPublicView | null = null;
  selectedPilotSubcription: Subscription;

  response: string = '';

  showCancelRequest = false;

  requestedClearanceKind: 'taxi' | 'expected' | '' = '';

  constructor(
    private readonly airportMapService: AirportMapService,
    private readonly mainPageService: MainPageService
  ) {}

  ngOnInit(): void {
    this.configSubscription();
  }

  ngOnDestroy(): void {
    this.selectedPilotSubcription?.unsubscribe();
  }

  configSubscription(): void {
    this.selectedPilotSubcription = this.airportMapService.selectedAircraft$.subscribe((aircraft) => {
      this.selectedPilot = aircraft;
      this.response = '';
    });
  }

  toggleDetails(): void {
    this.showDetails = !this.showDetails;
  }

  removeCoord(index: number): void {
    if (!this.clearance) return;
    this.clearance.coords.splice(index, 1);
  }

  // === LOGIQUE MÉTIER ===================================

  get stepCode(): string {
    if (!this.clearance) return '';
    return this.clearance.kind === 'expected' ? 'DM_136' : 'DM_135';
  }

  get step() {
    return this.selectedPilot?.steps?.[this.stepCode] ?? null;
  }

  get isRespondableStep(): boolean {
    const s = this.step;
    return !!s && [StepStatus.NEW, StepStatus.STANDBY, StepStatus.IDLE].includes(s.status);
  }

  get isStandby(): boolean {
    const s = this.step;
    return !!s && StepStatus.STANDBY == s.status;
  }

  get defaultMessage(): string {
    if (!this.clearance) return '';
    const label = this.clearance.kind === 'expected' ? 'expected taxi' : 'taxi clearance';
    return `Standby for ${label}`;
  }

  get unableMessage(): string {
    return `Unable to provide clearance at this time.`;
  }

  requestClearance(): void {
    const pilotSid = this.selectedPilot?.sid;
    if (!pilotSid || !this.requestedClearanceKind) return;
    this.mainPageService.fetchClearance(pilotSid, this.requestedClearanceKind);
    this.showCancelRequest = true;
    this.showDetails = true;
  }

  cancelClearance(): void {
      const pilotSid = this.selectedPilot?.sid;
      if (!pilotSid || !this.requestedClearanceKind) return;
      this.mainPageService.cancelClearance(pilotSid)
      this.showCancelRequest = false;
  }

  // requests to server
  emitAction(action: 'standby' | 'unable' | 'affirm'): void {
    const pilotSid = this.selectedPilot?.sid;
    if (!this.clearance || !pilotSid || !this.isRespondableStep || !this.step) return;

    const message =
      action === 'affirm'
        ? this.clearance.instruction
        : action === 'standby'
          ? this.defaultMessage
          : this.unableMessage;

    const payload = {
      pilot_sid: pilotSid,
      step_code: this.stepCode,
      action,
      message,
      request_id: this.step?.request_id || '',
    };

    this.mainPageService.sendResponse(payload);
    this.response = '';
    this.showDetails = false;
  }
}
