import { NgClass } from '@angular/common';
import { AfterViewInit, Component, ElementRef, Input, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { formatQuickResponse, getQReponseByStepCode, QuickResponse, StepCode } from '@app/interfaces/Messages';
import { StepUpdate } from '@app/interfaces/Payloads';
import { PilotPublicView, StepPublicView } from '@app/interfaces/Publics';
import { SelectedRequestInfo } from '@app/interfaces/SelectedRequest';
import { StepStatus } from '@app/interfaces/StepStatus';
import { AirportMapService } from '@app/services/airport-map.service';
import { MainPageService } from '@app/services/main-page.service';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-request-log',
  standalone: true,
  imports: [NgClass, FormsModule],
  templateUrl: './request-log.component.html',
  styleUrl: './request-log.component.scss'
})
export class RequestLogComponent implements OnInit, OnDestroy, AfterViewInit {
  @Input() step!: StepPublicView;
  @ViewChild('content') contentRef?: ElementRef<HTMLDivElement>;

  
  private selectedPlaneSubscription: Subscription;
  
  private selectedPilotSubscription: Subscription;
  
  // payload attributes
  selectedPilotSid: string = '';
  selectedAction: 'affirm' | 'standby' | 'unable' | null = null;
  response: string = '';
  selectedRequestInfo: SelectedRequestInfo; // only the stepCode
  selectedDirection: 'LEFT' | 'RIGHT' | null = null;
  // ----

  requestIdSubscription: Subscription;
  expanded = false;

  quickResponses : string[] = [];
  smartResponses: string[] = [];
  isLoadingSmartResponses = false;

  smartResponsesSubscription: Subscription;

  isRespondable: boolean = false;

  constructor(
    private readonly mainPageService: MainPageService,
    private readonly airportMapService: AirportMapService
  ) {}

  ngOnInit(): void {
    this.configSubscription();
    this.isRespondable = this.step.status !== StepStatus.RESPONDED;
    console.log('RequestLogComponent initialized with step:', this.isRespondable);
  }

  ngOnDestroy(): void {
    this.requestIdSubscription?.unsubscribe();
    this.smartResponsesSubscription?.unsubscribe();
    this.selectedPilotSubscription?.unsubscribe();
    this.selectedPlaneSubscription?.unsubscribe();
    if (this.expanded) this.selectRequest('', '');
    this.selectedDirection = null;
    this.response = '';
    this.selectedAction = null;
  }

  ngAfterViewInit(): void {
    if (this.expanded) {
      this.scrollToCard();
    }
  }

  configSubscription(): void {
    this.requestIdSubscription = this.mainPageService.selectedRequestId$.subscribe((requestInfo : SelectedRequestInfo) => {
      this.selectedRequestInfo = requestInfo;
      const isEmpty = requestInfo.stepCode || requestInfo.requestId;
      this.expanded = !!isEmpty && this.selectedRequestInfo.stepCode === this.step.step_code
      if (this.expanded) {
        this.isRespondable = ![StepStatus.RESPONDED, StepStatus.CLOSED].includes(this.step.status);
        this.quickResponses = getQReponseByStepCode(this.selectedRequestInfo.stepCode as StepCode);
      }
    })

    this.smartResponsesSubscription = this.mainPageService.smartResponses$.subscribe((responses: string[]) => {
      this.smartResponses = responses;
    });

    this.selectedPilotSubscription = this.mainPageService.selectedPilot$.subscribe((pilot: PilotPublicView | null) => {
      this.setSelectedPilotSid(pilot?.sid)
    });

    this.selectedPlaneSubscription = this.airportMapService.selectedPlane$.subscribe((plane: PilotPublicView | null) => {
      this.setSelectedPilotSid(plane?.sid)
    });
  }


  get statusClass(): string {
    return this.step?.status?.toLowerCase() ?? 'idle';
  }

  get formattedTime(): string {
    if (!this.step?.timestamp) return '';
    return new Date(this.step.timestamp * 1000).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit'
    });
  }
  
  // payload selection
  setSelectedPilotSid(sid: string = '') {
    if (!sid) return
    if (!this.selectedPilotSid) this.selectedPilotSid = sid;
    if (this.selectedPilotSid !== sid) this.selectedPilotSid = sid;
  }

  selectDirection(event : Event, dir: 'LEFT' | 'RIGHT') {
    event.stopPropagation();
    this.selectedDirection = dir;
    this.step.label = `PUSHBACK ${dir}`;
    this.step.message = `REQUEST PUSHBACK ${dir}`;
  }
  
  selectRequest(stepCode: string, requestId: string): void {
    const requestInfo: SelectedRequestInfo = { stepCode, requestId };
    this.mainPageService.selectRequest(requestInfo);
  }

  submitResponse(event: Event): void {
    event.stopPropagation();
    if (this.step?.step_code === 'DM_131' && !this.selectedDirection) {
      alert('Please select a direction for pushback (LEFT or RIGHT).');
      return;
    }
  
    const formattedResponse = this.response.trim();
    if (!formattedResponse) return;
  
    const payload: StepUpdate = {
      pilot_sid: this.selectedPilotSid,
      step_code: this.step.step_code,
      request_id: this.step.request_id || 'no_req_id', //! this is so shit
      message: formattedResponse,
      action: this.selectedAction || 'affirm'
    };

    this.mainPageService.sendResponse(payload);
    this.response = '';
    this.smartResponses = [];
    this.selectedAction = null;
    this.selectedDirection = null;
    this.selectRequest('', '');
  }

  setQuickResponse(text: string, event: MouseEvent): void {
    event.stopPropagation();
    const selectedStepCode = this.selectedRequestInfo?.stepCode as StepCode;
    if (!selectedStepCode) return;
    const formattedText = formatQuickResponse(text as QuickResponse, selectedStepCode);
    if (!formattedText) return;
  
    this.response = formattedText;
    this.selectedAction = text.toLowerCase() as 'affirm' | 'standby' | 'unable';
  }

  applySmart(text: string, event: MouseEvent): void {
    event.stopPropagation();
    this.response = text;
  }

  // visual
  scrollToCard(): void {
    requestAnimationFrame(() => {
      this.contentRef?.nativeElement.scrollIntoView({
        behavior: 'smooth',
        block: 'start'
      });
    });
  }

  toggleExpand(event: MouseEvent): void {
    event.stopPropagation();
    if (this.expanded) return this.selectRequest('', '');
    this.selectRequest(this.step.step_code, this.step.request_id);
    this.scrollToCard();
  }

  getStepTooltip(step: StepPublicView): string {
    return `
CODE: ${step.step_code}
STATUS: ${step.status}
LABEL: ${step.label}
MESSAGE: ${step.message}
TIME: ${this.formatTimestamp(step.timestamp)}
VALIDATED: ${this.formatTimestamp(step.validated_at)}
REQUEST ID: ${step.request_id}
`.trim();
  }

  formatTimestamp(ts: number | null | undefined): string {
    if (!ts) return '--';
    const date = new Date(ts * 1000);
    return date.toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  }
}
