import { Component, OnDestroy, OnInit } from '@angular/core';
import { PilotPublicView, StepPublicView } from '@app/interfaces/Publics';
import { MainPageService } from '@app/services/main-page.service';
import { Subscription } from 'rxjs';
import { RequestLogComponent } from './request-log/request-log.component';
import { StepStatus } from '@app/interfaces/StepStatus';
import { AirportMapService } from '@app/services/airport-map.service';

@Component({
  selector: 'app-selected-pilot',
  standalone: true,
  imports: [RequestLogComponent],
  templateUrl: './selected-pilot.component.html',
  styleUrl: './selected-pilot.component.scss'
})
export class SelectedPilotComponent implements OnInit, OnDestroy {
  private selectedPilotSubscription : Subscription;
  selectedPilot: PilotPublicView | null = null;

  activeSteps: StepPublicView[] = [];
  respondedSteps: StepPublicView[] = [];
  inactiveSteps: StepPublicView[] = [];

  constructor(
    private readonly mainPageService: MainPageService,
    private readonly airportMapService: AirportMapService
  ) {}

  ngOnInit(): void {
      this.configSubscription();
  }

  ngOnDestroy(): void {
    this.selectedPilotSubscription?.unsubscribe();
  }
  configSubscription(): void {
    this.selectedPilotSubscription = this.airportMapService.selectedPilot$
      .subscribe((pilot: PilotPublicView | null) => {
        this.selectedPilot = pilot;
        this.setStepArrays();
      });
  }
  
  setStepArrays(): void {
    this.activeSteps = [];
    this.respondedSteps = [];
    this.inactiveSteps = [];
  
    if (!this.selectedPilot) return;
  
    const steps = Object.values(this.mainPageService.getPilotSteps(this.selectedPilot.sid) ?? {});
    
    steps.forEach(step => {
      if (this.isActiveStatus(step.status)) {
        this.activeSteps.push(step);
      } else if (step.status === StepStatus.RESPONDED) {
        this.respondedSteps.push(step);
      } else {
        this.inactiveSteps.push(step);
      }
    });
  }
  
  isActiveStatus(status: StepStatus): boolean {
    return [
      StepStatus.NEW,
      StepStatus.STANDBY,
      StepStatus.EXECUTED,
      StepStatus.LOADED
    ].includes(status);
  }

  selectPilot(sid: string): void {
    this.mainPageService.selectPilot(sid);
    this.airportMapService.pilot = null;
  }

  getPilotColor(sid: string): string {
    return this.mainPageService.getPilotColor(sid);
  }

  getPilotStepsStatus(): StepPublicView[] {
    if (!this.selectedPilot) return [];
    const steps = this.mainPageService.getPilotSteps(this.selectedPilot.sid);
    return Object.values(steps);
  }
}
